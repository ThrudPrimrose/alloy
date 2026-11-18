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
import re
import signal
import sys
from typing import Any, NoReturn

from alloy.isa import ALIASES, OPS, ask, load, simt, tensix, tile
from alloy.isa.costs import costs
from alloy.isa.mathcheck import validate_kernel, validate_kernels
from alloy.isa.mathkernels import ALIASES as FUNCTION_ALIASES
from alloy.isa.mathkernels import (
    LADDER,
    LEVELS,
    cheapest,
    error_text,
    functions,
    ladder,
    libraries,
    library_function,
    render,
    target_of,
)
from alloy.isa.mathkernels import kernel as find
from alloy.isa.mathtime import ELEMENTS, time_function
from alloy.isa.schedules import legal, skeleton
from alloy.isa.schedules import verify as verify_skeleton
from alloy.isa.table import (
    ALL_DTYPES,
    FMA_FORM,
    NO_MATH,
    WIDTH_KNOBS,
    Hit,
    Table,
    gate,
    masked_form,
    normalized,
    suggestion,
)
from alloy.isa.validate import Verdict, emulated, host_can_run, validate, validate_all

#: The Tenstorrent target: tile calls checked on ttsim, kept apart from the SIMD table (alloy/isa/tensix.py).
TENSIX = "tensix"
#: GPU archs: ``tile`` and ``ask`` take them; ``lookup`` takes their SIMT dialect.
GPU_ARCHS = {"sm90": "cuda"} | dict.fromkeys(tile.CDNA, "hip")
#: Words for a matrix instruction: those live under ``tile`` and ``ask ... mma``, not ``lookup``.
MATRIX_WORDS = ("mma", "mfma", "wmma", "wgmma", "gemm", "matmul")
#: Prefixes of AMD GPU (CDNA) assembly mnemonics, which the instruction table (CPU only) does not index.
CDNA_MNEMONIC = re.compile(r"^(v_|s_|ds_|global_|buffer_|flat_|scratch_)")


def matrix_note(op: str) -> str:
    """Where a matrix instruction is answered, for an op that names one; else nothing."""
    if op.lower() not in MATRIX_WORDS:
        return ""
    return (
        f"; {op} is a matrix instruction: tile <arch> gemm M N K --in f16 --acc f32 gives a checked kernel, "
        "and ask <target> mma takes your operands"
    )


def refuse_gpu_arch(isa: str) -> None:
    """A GPU arch given to ``lookup``: name the dialect and the commands that take the arch."""
    if isa in GPU_ARCHS:
        raise KeyError(
            f"{isa}: a GPU arch; lookup takes its dialect ({GPU_ARCHS[isa]}, e.g. lookup {GPU_ARCHS[isa]} reduce_add f32), "
            f"and tile and ask take {isa}"
        )


class Parser(argparse.ArgumentParser):
    """argparse with a malformed command line exiting 64 (usage), like an invalid request: argparse's own 2 is the
    code of an infeasible answer, which the agent route returns as an answer."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        self.exit(USAGE, f"{self.prog}: error: {message}\n")


def main(argv: list[str] | None = None) -> int:
    parser = Parser(
        prog="alloy.isa",
        description="The machine abstract math ISA and its per-target intrinsic spellings.",
    )
    commands = parser.add_subparsers(dest="command", required=True, parser_class=Parser)

    lookup_p = commands.add_parser("lookup", help="op -> intrinsic: lookup <isa> <op> <dtype>")
    lookup_p.add_argument("isa", help="avx2, avx512 (also avx512_256), neon, sve; tensix, cuda, hip")
    lookup_p.add_argument("op", help=f"one of: {', '.join(OPS)}")
    lookup_p.add_argument("dtype", help="f64, f32, f16, i64 or i32")
    lookup_p.add_argument("--no-verify", action="store_true", help="skip the numerical validation gate")
    lookup_p.add_argument("--level", choices=LADDER, help="for a math function: one kernel level; default all three")
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
    kernel_p.add_argument("--level", choices=LADDER, help="one level; default strict, relaxed and fast")
    kernel_p.add_argument("--max-ulp", type=float, help="the cheapest kernel within this many ulp")
    kernel_p.add_argument(
        "--max-abs", type=float, help="the cheapest kernel within this absolute error, the worst over its whole range"
    )
    kernel_p.add_argument("--no-verify", action="store_true", help="skip the numerical validation gate")

    tiers_p = commands.add_parser("tiers", help="a function's polynomial depths, cheapest first: tiers sin")
    tiers_p.add_argument("function", help="sin, cos, exp or log (ln)")
    tiers_p.add_argument("--json", action="store_true", help="one JSON record per depth")

    time_p = commands.add_parser(
        "time", help="what an element costs here with each kernel and library call: time <isa> <function|all> <dtype>"
    )
    time_p.add_argument("isa", help="avx2 or avx512: an ISA this host runs")
    time_p.add_argument("function", help="a math function, or all")
    time_p.add_argument("dtype", help="f64 or f32")
    time_p.add_argument("--json", action="store_true", help="one JSON record per way to compute the function")

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

    tile_p = commands.add_parser("tile", help="a matrix tile's plan and checked program: tile cpu gemm 64 64 64")
    tile_p.add_argument("target", help="cpu, sme, sm90 (GH200), gfx942 (MI300A), or gfx90a (MI250X)")
    tile_p.add_argument("operation", choices=["gemm"])
    tile_p.add_argument("m", type=int)
    tile_p.add_argument("n", type=int)
    tile_p.add_argument("k", type=int)
    tile_p.add_argument("--in", dest="in_type", default="f32", help="input element type")
    tile_p.add_argument("--acc", dest="acc_type", default="f32", help="accumulator element type")
    tile_p.add_argument("--no-verify", action="store_true", help="skip the compile and run against a reference")
    tile_p.add_argument("--json", action="store_true", help="the plan as JSON")

    ask_p = commands.add_parser(
        "ask", help="any target, any operation: ask sm90 mma --a shared:f16:64x64:row_major:b128 ..."
    )
    ask_p.add_argument("target", help=", ".join(ask.TARGETS))
    ask_p.add_argument("op", help="an op of `ops`, a math function, mma, or copy")
    for name in ("a", "b", "c", "x", "src", "dst"):
        ask_p.add_argument(f"--{name}", help="operand as space:dtype[:RxC or N][:layout][:swizzle]")
    ask_p.add_argument("--unit", default="", help="pin the implementation (tma, warpgroup, mfma, vector, ...)")
    ask_p.add_argument("--on", default="", help="wait: the completion token (mbarrier, wgmma_group, lgkmcnt, ...)")
    ask_p.add_argument("--kind", default="", help="fence: proxy or operand")
    ask_p.add_argument("--max-ulp", type=float, help="for a math function: the cheapest rung within this bound")
    ask_p.add_argument("--no-verify", action="store_true", help="skip the check")
    ask_p.add_argument("--json", action="store_true", help="the Feasible, Infeasible, or Invalid answer as JSON")

    all_p = commands.add_parser(
        "ask-all",
        help="requests that run as one kernel: ask-all sm90 'copy src=global:f16:64x64 "
        "dst=shared:f16:64x64:row_major:b128' 'mma a=... b=... c=...'",
    )
    all_p.add_argument("target", help=", ".join(ask.TARGETS))
    all_p.add_argument("requests", nargs="+", help="op name=operand ... [unit=U] [max_ulp=X], one request per argument")
    all_p.add_argument("--no-verify", action="store_true", help="skip the check")
    all_p.add_argument("--json", action="store_true", help="the Combined, Infeasible, or Invalid answer as JSON")

    args = parser.parse_args(argv)
    for field in ("isa", "op", "dtype", "function", "target", "unit"):
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
    if args.command == "tile":
        return tile_command(args)
    if args.command == "ask":
        return ask_command(args)
    if args.command == "ask-all":
        return ask_all_command(args)
    if args.command == "kernel":
        level = args.level
        table.isa(args.isa)
        if args.max_ulp is not None or args.max_abs is not None:
            if level:
                raise KeyError("--level names one rung and --max-ulp/--max-abs pick one: give one of the two")
            picked = cheapest(args.function, args.dtype, args.isa, max_ulp=args.max_ulp, max_abs=args.max_abs)
            level = picked.kernel.level
        return print_kernels(table, args.isa, args.function, args.dtype, level, not args.no_verify)
    if args.command == "tiers":
        return tiers_command(table, args)
    if args.command == "time":
        return time_command(table, args)
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
    if isa in WIDTH_KNOBS:
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
    for cost in costs(isa, op, dtype):
        each = f"{cost.rthroughput:g} cycles each in a stream"
        numbers = cost.note or f"latency {cost.latency}, {each}, {cost.uops} uop(s)"
        print(f"  cost:      {cost.cpu} (llvm-mca): {cost.instruction}: {numbers}")
    for key in entry.approximations:
        tier = table.approx[key]
        print(f"  tier {key}: abs error {tier.error_abs:.3g} ({tier.error_ulp:.4g} f64 units of 2^-52); {tier.domain}")
    for library, call in entry.libraries.items():
        print(f"  {library}: {call}")
    if entry.note:
        print(f"  note:      {entry.note}")


def time_command(table: Table, args: argparse.Namespace) -> int:
    """Nanoseconds per element of every kernel of a function next to the library calls, measured now on this host."""
    table.isa(args.isa)
    names = functions() if args.function == "all" else (find(args.function, args.dtype, LEVELS[0]).fn,)
    for fn in names:
        rows = time_function(fn, args.dtype, args.isa)
        if not rows:
            raise KeyError(f"this host does not run {args.isa}/{args.dtype}, so nothing can be timed here")
        if args.json:
            for row in rows:
                print(json.dumps({"function": fn, "dtype": args.dtype, "isa": args.isa, **dataclasses.asdict(row)}))
            continue
        print(f"{fn} {args.dtype} on {args.isa}: ns per element of y[i] += {fn}(x[i]), {ELEMENTS} elements in cache")
        for row in rows:
            error = "" if row.error_ulp is None else f", {row.error_ulp:.3g} ulp, {row.intrinsics} intrinsics"
            print(f"  {row.name}: {row.ns:.2f} ns{error}")
    return 0


def tiers_command(table: Table, args: argparse.Namespace) -> int:
    """Every polynomial depth of a function, cheapest first, so the caller picks the error it can afford."""
    function = FUNCTION_ALIASES.get(args.function, args.function)
    tiers = sorted(
        ((name, tier) for name, tier in table.approx.items() if tier.op == function),
        key=lambda item: (len(item[1].recipe), -item[1].error_abs),
    )
    if not tiers:
        known = sorted({tier.op for tier in table.approx.values()})
        whole = "; `kernel` gives it whole" if function in functions() else ""
        raise KeyError(f"{args.function!r}: no polynomial tiers; tiers exist for {known}{whole}")
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
    if args.isa == TENSIX:
        return tensix_lookup(args.op, args.dtype, args.json)
    if args.isa in simt.DIALECTS:
        return simt_lookup(args.isa, args.op, args.dtype, args.json)
    refuse_gpu_arch(args.isa)
    refuse_width_knob(args.isa)
    table.isa(args.isa)  # an unknown ISA is named before the op
    gate(args.isa, args.dtype)
    op: str = args.op
    function = FUNCTION_ALIASES.get(op, op)
    if function not in OPS and function not in functions():
        if function.startswith("reduce_"):
            held = ", ".join(name for name in OPS if name.startswith("reduce_"))
            raise KeyError(f"{args.op!r}: the table holds only {held}, so no other reduction here is verified")
        raise KeyError(
            f"{args.op!r}: neither an abstract op nor a math function"
            f"{matrix_note(args.op) or suggestion(args.op, [*OPS, *functions()])}"
        )
    if function in OPS:
        verdict = None if args.no_verify else validate(args.isa, function, args.dtype, table)
        if verdict is not None and verdict.ok is False:
            return report_failure(verdict)
        if args.json:
            row = dataclasses.asdict(table.entry(args.isa, function, args.dtype))
            modelled = [dataclasses.asdict(c) for c in costs(args.isa, function, args.dtype)]
            print(
                json.dumps(
                    {
                        "isa": args.isa,
                        "op": function,
                        "dtype": args.dtype,
                        **row,
                        "costs": modelled,
                        "verdict": record(verdict),
                    }
                )
            )
            return 0
        print_entry(table, args.isa, function, args.dtype)
        if verdict is not None:
            print(f"{'verified' if verdict.ok else 'unverified'}: {verdict.basis}; {verdict.detail}".rstrip())
    if function in functions():
        if args.json:
            return print_kernels_json(table, args.isa, function, args.dtype, args.level, not args.no_verify)
        return print_kernels(table, args.isa, function, args.dtype, args.level, not args.no_verify)
    return 0


def tensix_lookup(op: str, dtype: str, as_json: bool) -> int:
    """Every Tensix row of ``op`` at ``dtype`` with its recorded ttsim verdict; exit 2 when a row failed its run, as a
    failed SIMD row does. A row without a current record is unverified, not failed."""
    found = [r for r in tensix.rows() if r.op == op]
    if not found:
        known = sorted({r.op for r in tensix.rows()})
        raise KeyError(f"tensix/{dtype}/{op}: no Tensix row{suggestion(op, known)} (rows: {', '.join(known)})")
    if dtype not in tensix.dtypes():
        raise KeyError(f"tensix/{dtype}/{op}: Tensix computes {', '.join(tensix.dtypes())} only (no f64)")
    verdicts = tensix.verdicts()
    picked = [(r, verdicts.get((op, dtype, r.unit))) for r in found]
    if as_json:
        print(
            json.dumps(
                [{**dataclasses.asdict(r), "verdict": None if v is None else dataclasses.asdict(v)} for r, v in picked]
            )
        )
        return 0
    print(f"tensix/{dtype}/{op}: {OPS[op].semantics if op in OPS else op}, applied to a 32x32 tile")
    run = tensix.recorded()
    for row, verdict in picked:
        print(f"  {row.unit} ({row.kind}): header {row.header}")
        for name, value in (("init", row.init), ("call", row.call)):
            spelled = value if isinstance(value, str) else ", ".join(f"{v} [{k}]" for k, v in value.items())
            print(f"    {name}: {spelled}")
        if verdict is None:
            print("    unverified: no recorded run")
        elif verdict.ok:
            # The ttsim run uses tt-metal 0.8x, so a row with per-version spellings is verified in its [v08] one only.
            which = "" if isinstance(row.init, str) and isinstance(row.call, str) else ", the [v08] spelling only"
            print(
                f"    verified on ttsim {run.get('ttsim', '').split(' ')[0]} (simulated Blackhole) with tt-metal 0.8x"
                f"{which}: max rel error {verdict.rel:.2g}"
            )
        else:
            print(f"    FAILED on ttsim: {verdict.error[:200]}")
        if row.note:
            print(f"    note: {row.note}")
    print(f"  note: {tensix.table()['target']['note']}")
    return 2 if any(v is not None and not v.ok for _, v in picked) else 0


def simt_lookup(dialect: str, op: str, dtype: str, as_json: bool) -> int:
    """The CUDA or HIP row of ``op`` at ``dtype`` with its recorded check."""
    found = [r for r in simt.rows() if op in (r.op, r.answers())]
    if not found:
        known = list(dict.fromkeys(r.answers() for r in simt.rows()))
        hint = matrix_note(op) or suggestion(op, known)
        raise KeyError(f"{dialect}/{op}: no SIMT row{hint} (rows: {', '.join(known)})")
    typed = [r for r in found if r.dtype == dtype]
    if not typed:
        dtypes = ", ".join(sorted({r.dtype for r in found}))
        raise KeyError(f"{dialect}/{dtype}/{op}: the {op} rows are {dtypes}; ask with one of those")
    row = typed[0]
    verdict = simt.verdicts().get((row.op, dialect))
    if as_json:
        print(
            json.dumps({**dataclasses.asdict(row), "verdict": None if verdict is None else dataclasses.asdict(verdict)})
        )
        return 0
    lanes = simt.LANES[dialect]
    print(f"{dialect}/{dtype}/{op}: one {f'warp of {lanes}' if row.kind == 'warp' else 'thread'}")
    print(f"  code:  {row.spelled(dialect)}")
    print(f"  {simt.bindings(dialect)}")
    if row.note:
        print(f"  note:  {row.note}")
    print(f"  {dialect}: {simt.table()['target'][dialect]['note']}")
    if verdict is None:
        print("unverified: no recorded check")
        return 0
    state = {True: "verified", False: "FAILED", None: "unverified"}[verdict.ok]
    error = f"; max rel error {verdict.rel:.2g}" if verdict.rel is not None else ""
    print(f"{state}: {verdict.basis}{error}")
    return 2 if verdict.ok is False else 0


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


def ladder_line(function: str, dtype: str, target: str) -> str:
    """Every kernel of ``function`` with its error and its cost, most accurate first."""
    return "; ".join(
        f"{k.level} {error_text(k)}, {render(k, target).intrinsics} intrinsics" for k in ladder(function, dtype)
    )


def print_kernels_json(table: Table, isa: str, function: str, dtype: str, level: str | None, verify: bool) -> int:
    """The kernels of a function as one JSON list, one record per rung, as the text form prints them (A9.6); a rung
    that fails its gate is left out and the exit code is 3."""
    table.isa(isa)
    target = target_of(isa)
    find(function, dtype, level or LEVELS[0])
    records, status = [], 0
    for name in (level,) if level else LEVELS:
        k = find(function, dtype, name)
        spelled = render(k, target)
        verdict = validate_kernel(k.fn, dtype, name, target) if verify else None
        if verdict is not None and verdict.ok is False:
            status = 3
            continue
        records.append({
            "function": function, "dtype": dtype, "isa": isa, "level": name, "error_ulp": k.error_ulp,
            "error_abs": k.error_abs, "contract": k.contract, "branch": bool(k.guard),
            "intrinsics": spelled.intrinsics, "source": spelled.source,
            "libraries": libraries(function, dtype, target, name),
            "verdict": None if verdict is None else {"ok": verdict.ok, "basis": verdict.basis},
        })  # fmt: skip
    print(json.dumps(records))
    return status


def print_kernels(table: Table, isa: str, function: str, dtype: str, level: str | None, verify: bool) -> int:
    """The kernels as C. Exit code 3 when one fails its gate."""
    table.isa(isa)
    target = target_of(isa)
    status = 0
    find(function, dtype, level or LEVELS[0])  # an unknown function or dtype is refused before anything prints
    if not level:
        print(f"// ladder: {ladder_line(function, dtype, target)}")
        print("// --level <name> gives one; --max-ulp N or --max-abs E gives the cheapest that holds the bound\n")
    for name in (level,) if level else LEVELS:
        k = find(function, dtype, name)
        spelled = render(k, target)
        branch = "one cold branch to scalar libm" if k.guard else "no branch"
        scope = f"any input; vector path for {k.contract}" if name == "strict" else f"contract: {k.contract}"
        basis = "over every input of its range" if k.exhaustive else "sampled"
        lines = [
            f"// {name}: {k.error_ulp:.4g} ulp {basis}; {spelled.intrinsics} intrinsics; {branch}; {scope}",
            spelled.source,
            *(f"// or call {library}: {call}" for library, call in libraries(function, dtype, target, name).items()),
        ]
        failed = False
        if verify:
            verdict = validate_kernel(k.fn, dtype, name, target)
            lines.append(f"// {MARKS[verdict.ok]}: {verdict.basis}; {verdict.detail}")
            failed = verdict.ok is False
        # a kernel that fails its gate is not an answer: it goes to stderr
        print("\n".join(lines) + "\n", file=sys.stderr if failed else sys.stdout)
        status = 3 if failed else status
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
    if hit.via == "scalar":
        return f"{name} = {hit.op} on one lane ({hit.dtype}), the scalar form of {hit.entry.mnemonic}"
    detail = {
        "intrinsic": hit.entry.intrinsic,
        "masked": hit.entry.masked,
        "recipe": " -> ".join(hit.entry.recipe),
        "library": name,
        "mnemonic": hit.entry.mnemonic,
    }[hit.via]
    semantics = f"\n  {hit.entry.semantics}" if hit.entry.semantics else ""
    return f"{name} = {hit.op} on {hit.isa}/{hit.dtype} ({hit.via}: {detail}){semantics}"


#: What a register in a pasted line says about its ISA.
REGISTERS = (
    (re.compile(r"zmm\d"), "avx512"),
    (re.compile(r"ymm\d"), "avx2"),
    (re.compile(r"\bz\d+\.[bhsd]|\bp\d+/[mz]"), "sve"),
    (re.compile(r"\bv\d+\.\d*[bhsd]"), "neon"),
)


def narrowed(line: str, hits: tuple[Hit, ...]) -> tuple[Hit, ...]:
    """The ``hits`` of the ISA the registers of ``line`` name; all of them when the line names none or none is left."""
    isas = {isa for register, isa in REGISTERS if register.search(line)}
    return tuple(hit for hit in hits if hit.isa in isas) or hits


def print_hits(table: Table, name: str, as_json: bool = False) -> None:
    hits = narrowed(name, table.reverse(name))
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
            print(hit_text(token, hit))
    elif table.assist(name):
        print_assists(table, name)
    elif token in NO_MATH:
        print(f"{token}: {NO_MATH[token]}")
    elif (found := library_function(token)) is not None:
        print(f"{token} = {found[0]} ({found[1]}) on {found[2]}: a vector math library call")
    else:
        if CDNA_MNEMONIC.match(token):
            matrix = "; tile gfx90a|gfx942 gemm ... gives a checked v_mfma kernel" if token.startswith("v_mfma") else ""
            raise KeyError(
                f"{name!r}: an AMD GPU (CDNA) instruction; the table indexes CPU instructions only{matrix}. "
                "For GPU code: lookup hip <op> f32 (wavefront rows), tile, or ask"
            )
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
    target = tensix.table()["target"]
    print(f"{TENSIX:8} {target['title']}  [tile calls, not intrinsics; {', '.join(tensix.dtypes())}]")
    print(f"  {target['note']}")
    for dialect in simt.DIALECTS:
        target = simt.table()["target"][dialect]
        print(f"{dialect:8} {target['title']}  [device code per thread or warp; f32]")
        print(f"  {target['note']}")


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
    text = skeleton(table, isa, schedule, dtype)
    failed = False
    if verify:
        verdict = verify_skeleton(isa, schedule, dtype, table)
        text += f"\n// {MARKS[verdict.ok]}: {verdict.basis}; {verdict.detail}"
        failed = verdict.ok is False
    print(text, file=sys.stderr if failed else sys.stdout)
    return 3 if failed else 0


def tile_command(args: argparse.Namespace) -> int:
    """A tile's plan: its steps, layout, descriptors, and program, checked here unless ``--no-verify``; exit 3 when
    the check could not run or failed, as an unverified lookup does."""
    found = tile.plan(args.target, args.m, args.n, args.k, args.in_type, args.acc_type)
    if not args.no_verify:
        found = tile.verify(found)
    if args.json:
        print(json.dumps(dataclasses.asdict(found)))
        return 0 if found.verified == "run" else 3
    print(f"{found.target}: gemm {found.m}x{found.n}x{found.k}, {found.in_type} in, {found.acc_type} accumulate")
    print(f"  check: {found.verified}" + (f" ({found.detail})" if found.detail else ""))
    print(f"  layout: {found.layout}")
    for name, value in found.descriptors.items():
        print(f"  {name}: {value}")
    print("  steps:")
    for step in found.steps:
        print(f"    {step}")
    print("  program:")
    print(found.program)
    return 0 if found.verified == "run" else 3


#: The exit code of an invalid request (sysexits' EX_USAGE), apart from 2, an infeasible one.
USAGE = 64


def ask_command(args: argparse.Namespace) -> int:
    """One request of the unified ISA (:mod:`alloy.isa.ask`); exit 0 when feasible, 2 when infeasible (the target
    cannot), and 64 when invalid (the request is wrong on every target, or an operand does not parse)."""
    answer: ask.Answer
    try:
        operands = {
            name: ask.Operand.parse(value)
            for name in ("a", "b", "c", "x", "src", "dst")
            if isinstance(value := vars(args).get(name), str)
        }
    except KeyError as exc:
        answer = ask.bad(None, ask.Why.MALFORMED, str(exc.args[0]), "space:dtype[:RxC or N][:layout][:swizzle]")
    else:
        request = ask.Request(
            args.target, args.op, operands, args.unit, args.max_ulp, args.on.lower(), args.kind.lower()
        )
        answer = ask.ask(request, verify=not args.no_verify)
    code = {"feasible": 0, "infeasible": 2, "invalid": USAGE}[answer.status]
    if args.json:
        print(json.dumps(dataclasses.asdict(answer)))
        return code
    if not isinstance(answer, ask.Feasible):
        print_refusal(f"{args.target} {args.op}", answer)
        return code
    print_feasible(f"{args.target} {args.op}", answer)
    return 0


def print_refusal(title: str, answer: ask.Infeasible | ask.Invalid) -> None:
    print(f"{title}: {answer.status} ({answer.why.value}): {answer.reason}")
    near = answer.nearest if isinstance(answer, ask.Infeasible) else answer.expected
    for line in near:
        print(f"  {'nearest' if isinstance(answer, ask.Infeasible) else 'expected'}: {line}")
    if isinstance(answer, ask.Infeasible) and answer.block:
        print(f"  block: {'x'.join(map(str, answer.block))} (a shape the target takes is a whole multiple)")
    if isinstance(answer, ask.Infeasible) and answer.fix:
        print(f"  fix: {answer.fix}")


def checked(check: ask.Check) -> str:
    """The check as one phrase; a basis that starts with its status ("compiled for gfx942") is not repeated."""
    said = check.basis.split(" ", 1)[0] in (check.status, "ran")  # "compiled for ...", "ran on ..."
    return check.basis if said else f"{check.status} {check.basis}".rstrip()


def print_feasible(title: str, answer: ask.Feasible) -> None:
    print(f"{title}: feasible on {answer.unit}; check: {checked(answer.check)}")
    for step in answer.steps:
        print(f"  {step.count} x {step.unit}: {step.spelling}" if step.count > 1 else f"  {step.unit}: {step.spelling}")
    for key, value in answer.setup.items():
        print(f"  setup {key}: {value}")
    for note in answer.notes:
        print(f"  note: {note}")
    if answer.completion is not None:
        done = answer.completion
        fences = f"; before it: {', '.join(done.fences)}" if done.fences else ""
        print(f"  async: completes on {done.token}: {done.wait}{fences}")
    print(answer.code)


def parsed_request(target: str, text: str) -> ask.Request:
    """One request of ``ask-all``: ``op name=operand ... [unit=U] [max_ulp=X]``; a malformed one raises
    :class:`KeyError` with what is wrong."""
    if not text.split():
        raise KeyError("an empty request: op name=operand ...")
    op, *fields = text.split()
    operands: dict[str, ask.Operand] = {}
    unit, max_ulp, on, kind = "", None, "", ""
    for field in fields:
        name, sep, value = field.partition("=")
        if not sep or not value:
            raise KeyError(f"{field!r} in {text!r}: a field is name=operand, unit=U, max_ulp=X, on=TOKEN, or kind=K")
        if name == "unit":
            unit = value.lower()
        elif name == "on":
            on = value.lower()
        elif name == "kind":
            kind = value.lower()
        elif name == "max_ulp":
            try:
                max_ulp = float(value)
            except ValueError:
                raise KeyError(f"{field!r} in {text!r}: max_ulp is a number") from None
        else:
            operands[name] = ask.Operand.parse(value)
    return ask.Request(target, op.lower(), operands, unit, max_ulp, on, kind)


def ask_all_command(args: argparse.Namespace) -> int:
    """Requests that run as one kernel (:func:`alloy.isa.ask.ask_all`); exit 0, 2, or 64 as ``ask``."""
    answer: ask.Combined | ask.Infeasible | ask.Invalid
    try:
        requests = [parsed_request(args.target, text) for text in args.requests]
    except KeyError as exc:
        answer = ask.bad(None, ask.Why.MALFORMED, str(exc.args[0]), "op name=space:dtype[:RxC or N][:layout][:swizzle]")
    else:
        answer = ask.ask_all(requests, verify=not args.no_verify)
    code = {"feasible": 0, "infeasible": 2, "invalid": USAGE}[answer.status]
    if args.json:
        print(json.dumps(dataclasses.asdict(answer)))
        return code
    if not isinstance(answer, ask.Combined):
        print_refusal(f"{args.target} kernel", answer)
        return code
    print(f"{args.target} kernel: feasible; check: {checked(answer.check)}")
    for line in answer.feeds:
        print(f"  {line}")
    for line in answer.order:
        print(f"  order: {line}")
    for i, one in enumerate(answer.answers):
        print_feasible(f"[{i}] {one.request.op}", one)
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    sys.exit(main())
