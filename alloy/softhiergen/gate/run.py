# Copyright 2026 ETH Zurich and the Alloy authors.
"""The gate: ``prepare <folder>`` lowers and generates every program into a subfolder; ``build_run.sh`` in each runs
it next to GVSoC (``ault.sh``); ``check <folder>`` compares the dumped arrays with NumPy and prints the table."""

import pathlib
import re
import sys
import traceback

import numpy

from alloy.softhiergen import program
from alloy.softhiergen.gate.programs import cases, collective_cases, placement_cases


def yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def prepare(root: pathlib.Path) -> None:
    for case in cases() + collective_cases() + placement_cases():
        folder = root / slug(case.name)
        try:
            sdfg = case.sdfg()
            program.write_folder(folder, sdfg, program.generate(sdfg), case.inputs)
            print(f"{case.name}: generated")
        except Exception:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "lowering_error.txt").write_text(traceback.format_exc())
            print(f"{case.name}: LOWERING FAILED\n{traceback.format_exc()}")


def check(root: pathlib.Path) -> bool:
    print("| program | builds | runs | correct | cycles |\n|---|---|---|---|---|")
    passed = True
    for case in cases() + collective_cases() + placement_cases():
        folder = root / slug(case.name)
        log = (folder / "build_run.log").read_text() if (folder / "build_run.log").exists() else ""
        built, ran = "DSH-BUILT" in log, "DSH-RAN" in log
        correct, cycles, note = False, "", ""
        if ran:
            try:
                arrays, count = program.read_results(folder)
                cycles = str(count)
                errors = []
                for name, want in case.expected.items():
                    got = arrays[name].astype(numpy.float64)
                    scale = max(float(numpy.abs(want).max()), 1e-30)
                    errors.append(float(numpy.abs(got - want).max()) / scale)
                correct = max(errors) <= case.tolerance
                note = f" (rel {max(errors):.2g})"
            except ValueError as error:
                note = f" ({error})"
        passed &= correct
        print(f"| {case.name} | {yes_no(built)} | {yes_no(ran)} | {yes_no(correct)}{note} | {cycles} |")
    return passed


if __name__ == "__main__":
    command, root = sys.argv[1], pathlib.Path(sys.argv[2])
    if command == "prepare":
        prepare(root)
    else:
        sys.exit(0 if check(root) else 1)
