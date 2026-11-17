# Copyright 2026 ETH Zurich and the Alloy authors.
"""Maintainer tool: writes ``alloy/isa/costs.toml`` (``python helpers/isacost.py``). Each table row with a mnemonic is
compiled alone (``validate.row_unit``) by clang to assembly for its ISA, and the instructions that spell the row's
mnemonic go through ``llvm-mca -instruction-info`` for the CPU :data:`alloy.isa.costs.CPUS` names: µops, latency and
reciprocal throughput. A row whose instruction the compiler folded away or replaced records nothing."""

import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

from alloy.isa.costs import CPUS, DEFAULT_PATH, Cost
from alloy.isa.table import ALL_DTYPES, Entry, Table, load
from alloy.isa.validate import CROSS, NOT_MNEMONICS, c_flags, row_unit

#: One row of llvm-mca's instruction info: µops, latency, reciprocal throughput, the flag columns, the instruction.
INFO_ROW = re.compile(r"^\s*(\d+)\s+(\d+)\s+(\d+\.\d+)\s+(?:[*U]\s+)*(\S.*?)\s*$")
#: An instruction line of clang's assembly: a tab, a mnemonic, maybe operands; labels and directives excluded.
ASM_LINE = re.compile(r"^\t([a-z][a-z0-9.]*)(?:\t(.*))?$")
TIMEOUT = 60
#: Rows whose instruction is a memory access: their memory operand is the op itself, so it stays.
MEMORY_OPS = frozenset({"load", "store", "gather", "scatter", "broadcast"})
#: An AT&T memory operand, ``8(%rsi,%rax,8)``, and the widest vector register an instruction names.
MEMORY_OPERAND = re.compile(r"[\w.$+-]*\(%\w+(?:,\s*%\w+)?(?:,\s*\d+)?\)(?:\{1to\d+\})?")
VECTOR_REGISTER = re.compile(r"%([xyz])mm\d+")


def target_flags(isa: str, dtype: str) -> list[str]:
    """clang flags that build ``isa`` rows: the validator's, with the triple and architecture an aarch64 row needs."""
    if isa in CROSS:
        arch = f"{CROSS[isa]}+fp16" if dtype == "f16" else CROSS[isa]
        return ["--target=aarch64-linux-gnu", f"-march={arch}"]
    return [*c_flags(isa, dtype), f"-mtune={CPUS[isa]}"]


def assembly(source: str, flags: list[str]) -> list[str]:
    """The instruction lines of ``source``'s function ``row`` compiled at -O1."""
    with tempfile.TemporaryDirectory(prefix="alloy_cost_") as tmp:
        unit = Path(tmp) / "row.c"
        unit.write_text(source)
        built = subprocess.run(
            ["clang", "-O1", "-S", "-o", "-", *flags, str(unit)],
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT,
        )
    if built.returncode != 0:
        raise RuntimeError(built.stderr.strip()[:300])
    return [line.strip() for line in built.stdout.splitlines() if ASM_LINE.match(line)]


#: Forms clang prints for a row's mnemonic: the float-domain twin of an integer bitwise op or move, a compare with
#: its operands swapped, Arm's bit insert for a bit select, SVE's mov alias of sel. Longest key first.
TWINS = {
    "vpbroadcastq": ("vbroadcastsd",),
    "vpbroadcastd": ("vbroadcastss",),
    "vpcmpltu": ("vpcmpnleu",),
    "vpcmplt": ("vpcmpgt",),
    "vmovdqu": ("vmovup",),
    "vpandn": ("vandnp",),
    "vpand": ("vandp",),
    "vpxor": ("vxorp",),
    "vpor": ("vorp",),
    "kand": ("vptestm",),
    "kor": ("vpor", "vptestm"),
    "bsl": ("bit", "bif"),
    "sel": ("mov",),
}
#: What the gate's frame puts around a row: memory moves, the mask-to-ones conversion, the predicate, the return.
FRAME = ("vmovup", "vmovdq", "vmovs", "vpmovm2", "vpsrl", "vzeroupper", "ret", "ldr", "str", "ld1", "st1", "whilelt",
         "ptrue", "mov")  # fmt: skip


def twins(word: str) -> tuple[str, ...]:
    return next((forms for key, forms in TWINS.items() if word.startswith(key)), ())


def starting(lines: list[str], forms: list[str]) -> list[str]:
    return [line for line in lines if forms and line.split()[0].startswith(tuple(forms))]


def matching(lines: list[str], entry: Entry) -> list[str]:
    """Every instruction, repeats included, that spells ``entry``: its mnemonic's words or observed forms, else their
    twins, else whatever the row compiled to past the frame. A composite ending in ``...`` keeps every instruction of
    the row, so a reduction counts each add and keeps its shuffles."""
    words = [w.split(" ")[0] for w in re.split(r"\s*\+\s*", entry.mnemonic) if w and w not in NOT_MNEMONICS]
    own = [line for line in lines if not line.split()[0].startswith(FRAME)]
    if entry.mnemonic.endswith("..."):
        return own
    return starting(lines, [*words, *entry.observed]) or starting(lines, [t for w in words for t in twins(w)]) or own


def register_form(instruction: str, op: str) -> str:
    """An x86 arithmetic ``instruction`` with its folded load replaced by a register of its own width: clang folds a
    row's operand load, and the row's cost is the arithmetic's, not the load's."""
    widths = VECTOR_REGISTER.findall(instruction)
    if op in MEMORY_OPS or not widths or MEMORY_OPERAND.search(instruction) is None:
        return instruction
    widest = max(widths, key="xyz".index)
    return MEMORY_OPERAND.sub(f"%{widest}mm15", instruction, count=1)


def mca(instructions: list[str], isa: str) -> list[Cost]:
    """llvm-mca's instruction info for ``instructions`` on the CPU of ``isa``."""
    cpu = CPUS[isa]
    triple = ["-mtriple=aarch64"] if isa in CROSS else []
    run = subprocess.run(
        ["llvm-mca", *triple, f"-mcpu={cpu}", "-instruction-info", "-iterations=1", "-"],
        input="\n".join(instructions) + "\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=TIMEOUT,
    )
    if run.returncode != 0:
        raise RuntimeError(run.stderr.strip()[:300])
    rows = [m for line in run.stdout.splitlines() if (m := INFO_ROW.match(line))]
    return [Cost(cpu, " ".join(m.group(4).split()), int(m.group(1)), int(m.group(2)), float(m.group(3))) for m in rows]


def directional(lines: list[str], op: str) -> list[str]:
    """A load row's reading instructions or a store row's writing ones (each row's unit does both); AT&T puts the
    source first, so a load's memory operand precedes its register and a store's follows it."""
    if op not in ("load", "store"):
        return lines

    def reads(line: str) -> bool:
        memory, register = MEMORY_OPERAND.search(line), VECTOR_REGISTER.search(line)
        return memory is not None and register is not None and memory.start() < register.start()

    x86 = [line for line in lines if VECTOR_REGISTER.search(line)]
    if not x86:  # aarch64: the mnemonic tells the direction
        return [line for line in lines if line.split()[0].startswith("ld" if op == "load" else "st")]
    return [line for line in x86 if reads(line) == (op == "load")]


def row_costs(lines: list[str], isa: str, op: str) -> list[Cost]:
    """llvm-mca's costs of ``lines`` in register form, or as compiled when the assembler rejects a register form
    (a conversion's narrower source)."""
    if not lines:
        return []
    try:
        return mca([register_form(line, op) for line in lines], isa)
    except RuntimeError:
        return mca(lines, isa)


#: Why llvm-mca's x86 numbers of a row are not a model: znver4 has no entry for gathers and scatters.
NOT_MODELLED = "not modelled: llvm-mca's znver4 model has no gather or scatter entry"


def measured(table: Table) -> Iterator[tuple[str, list[Cost]]]:
    for isa, target in table.isas.items():
        for dtype in ALL_DTYPES:
            for op, entry in target.entries(dtype).items():
                if not entry.mnemonic or entry.approximations:
                    continue
                if op in ("gather", "scatter") and isa not in CROSS:
                    yield f"{isa}/{dtype}/{op}", [Cost(CPUS[isa], entry.mnemonic, 0, 0, 0.0, NOT_MODELLED)]
                    continue
                try:
                    compiled = assembly(row_unit(isa, dtype, op, table), target_flags(isa, dtype))
                    named = matching(compiled, entry)
                    renamed = not named and op in ("load", "store")  # a move of another name moves the same bytes
                    if renamed:
                        named = [line for line in compiled if MEMORY_OPERAND.search(line) or "[" in line]
                    picked = directional(named, op)
                    found = row_costs(picked[:1] if renamed else picked, isa, op)
                except (RuntimeError, subprocess.TimeoutExpired) as err:
                    print(f"{isa}/{dtype}/{op}: {err}", file=sys.stderr)
                    continue
                if found:
                    yield f"{isa}/{dtype}/{op}", found


def toml_text(rows: dict[str, list[Cost]]) -> str:
    head = [
        "# Written by helpers/isacost.py: llvm-mca's model of each table row's compiled instructions (alloy/isa/costs.py).",
        f"# CPUs: {', '.join(sorted(set(CPUS.values())))}. Do not edit by hand; rerun the helper after a table change.",
        "",
    ]
    body = []
    for key in sorted(rows):
        for c in rows[key]:
            body += [
                f'[[rows."{key}"]]',
                f"cpu = {json.dumps(c.cpu)}",
                f"instruction = {json.dumps(c.instruction)}",
                f"uops = {c.uops}",
                f"latency = {c.latency}",
                f"rthroughput = {c.rthroughput}",
                *([f"note = {json.dumps(c.note)}"] if c.note else []),
                "",
            ]
    return "\n".join(head + body)


def main() -> int:
    rows = dict(measured(load()))
    DEFAULT_PATH.write_text(toml_text(rows))
    print(f"{len(rows)} rows -> {DEFAULT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
