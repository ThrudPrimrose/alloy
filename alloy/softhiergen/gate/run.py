# Copyright 2026 ETH Zurich and the Alloy authors.
"""The gate: ``prepare <folder>`` lowers and generates every program into a subfolder; ``build_run.sh`` in each runs
it next to GVSoC (``ault.sh``); ``check <folder>`` compares the dumped arrays with NumPy and prints the table."""

import pathlib
import re
import shutil
import sys
import traceback

import numpy

from alloy.gate import error
from alloy.softhiergen import program
from alloy.softhiergen.gate.programs import all_cases

#: Generated programs with one call swapped, by the case they copy: the check must call each wrong
PLANTED = {"planted: vector add is sub": ("vector add", "dsh_rvv_add_f32(", "dsh_rvv_sub_f32(")}


def yes_no(flag: bool) -> str:
    return "yes" if flag else "no"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def prepare(root: pathlib.Path) -> None:
    for case in all_cases():
        folder = root / slug(case.name)
        try:
            sdfg = case.sdfg()
            program.write_folder(folder, sdfg, program.generate(sdfg), case.inputs)
            print(f"{case.name}: generated")
        except Exception:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "lowering_error.txt").write_text(traceback.format_exc())
            print(f"{case.name}: LOWERING FAILED\n{traceback.format_exc()}")
    for name, (source, call, wrong) in PLANTED.items():
        src, dst = root / slug(source), root / slug(name)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        kernels = (dst / "kernels.cpp").read_text()
        assert call in kernels, f"{source}: no {call} to plant over"
        (dst / "kernels.cpp").write_text(kernels.replace(call, wrong))
        (dst / "build_run.sh").write_text((dst / "build_run.sh").read_text().replace(str(src), str(dst)))
        print(f"{name}: planted")


def outcome(
    folder: pathlib.Path, expected: dict[str, numpy.ndarray], tolerance: float
) -> tuple[bool, bool, bool, str, str]:
    """Built, ran, correct, cycles and a note of one program folder."""
    log = (folder / "build_run.log").read_text() if (folder / "build_run.log").exists() else ""
    built, ran = "DSH-BUILT" in log, "DSH-RAN" in log
    if not ran:
        return built, ran, False, "", ""
    try:
        arrays, count = program.read_results(folder)
    except ValueError as err:
        return built, ran, False, "", f" ({err})"
    worst = max(error(arrays[name], want) for name, want in expected.items())
    return built, ran, worst <= tolerance, str(count), f" (rel {worst:.2g})"


def check(root: pathlib.Path) -> bool:
    print("| program | builds | runs | correct | cycles |\n|---|---|---|---|---|")
    every = {case.name: case for case in all_cases()}
    passed = True
    for case in every.values():
        built, ran, correct, cycles, note = outcome(root / slug(case.name), case.expected, case.tolerance)
        passed &= correct
        print(f"| {case.name} | {yes_no(built)} | {yes_no(ran)} | {yes_no(correct)}{note} | {cycles} |")
    for name, (source, _, _) in PLANTED.items():
        case = every[source]
        built, ran, correct, cycles, note = outcome(root / slug(name), case.expected, case.tolerance)
        caught = built and ran and not correct  # the check fails a wrong program that ran
        passed &= caught
        print(f"| {name} | {yes_no(built)} | {yes_no(ran)} | {'caught' if caught else 'NOT CAUGHT'}{note} | {cycles} |")
    return passed


if __name__ == "__main__":
    command, root = sys.argv[1], pathlib.Path(sys.argv[2])
    if command == "prepare":
        prepare(root)
    else:
        sys.exit(0 if check(root) else 1)
