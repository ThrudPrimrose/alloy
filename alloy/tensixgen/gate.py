# Copyright 2026 ETH Zurich and the Alloy authors.
"""The shared gate's programs (:mod:`alloy.gate`, the cases of :mod:`alloy.softhiergen.gate.programs`) through the
Tensix kernel split: each case either becomes a Tensix program or is refused with the reason, so one table shows what
each tile backend lowers.

    python -m alloy.tensixgen.gate          # one line per case: generated, or the refusal
    python -m alloy.tensixgen.gate run      # and every generated program on ttsim (docker), checked by alloy.gate.error

A run writes each program with the case's inputs (``inputs.npz``); ttsim_host.py runs them and saves the output, which
:func:`alloy.gate.error` compares with the case's reference at its tolerance. A planted program (vector add with the
add swapped for a sub) must come out wrong.
"""

import pathlib
import sys
import tempfile

import numpy

from alloy import tilelower
from alloy.gate import Case, error
from alloy.softhiergen.gate.programs import all_cases
from alloy.tensixgen import collectives, ttsim
from alloy.tensixgen.backend import Refused
from alloy.tensixgen.split import Program, program
from alloy.tensixgen.tasks import LANES


def task_of(case: Case) -> dict[str, object]:
    """The eval-task form the split takes: the case's array inputs, its one output, map or reduce by its size."""
    if len(case.expected) != 1:
        raise Refused(f"{case.name}: {len(case.expected)} outputs; a Tensix program writes one")
    ((output, want),) = case.expected.items()
    inputs = [[name, 0.0, 1.0] for name, value in case.inputs.items() if numpy.ndim(value) > 0]
    return {"name": case.name, "inputs": inputs, "output": output, "kind": "reduce" if want.size == 1 else "map",
            "program": [case.name]}  # fmt: skip


def lowered(case: Case) -> Program:
    """The case's Tensix program; raises :class:`Refused` (or DaCe's error) when the split does not take it."""
    sdfg = case.sdfg()
    if (node := collectives.comm_node(sdfg)) is not None:
        return collectives.program(task_of(case), sdfg, node)
    tilelower.front(sdfg, LANES, fuse_multiply_add=False)
    scalars = {name: float(value) for name, value in case.inputs.items() if numpy.ndim(value) == 0}
    return program(task_of(case), sdfg, scalars, version="v08")  # ttsim's tt-metal


#: Programs with one call swapped, by the case they copy: the check must call each wrong.
PLANTED = {"planted: vector add is sub": ("vector add", "add_binary_tile", "sub_binary_tile")}


def generated() -> tuple[dict[str, tuple[Case, Program]], dict[str, str]]:
    """Every shared case's Tensix program, and the refusal of every other case."""
    made, refused = {}, {}
    for case in all_cases():
        try:
            made[case.name] = (case, lowered(case))
        except Exception as err:  # every refusal is a row of the table, whatever raised it
            refused[case.name] = f"{type(err).__name__}: {str(err).splitlines()[0][:160]}"
    for name, (source, call, wrong) in PLANTED.items():
        case, prog = made[source]
        assert call in prog.compute, f"{source}: no {call} to plant over"
        made[name] = (case, Program(name, prog.reader, prog.compute.replace(call, wrong), prog.writer, prog.config,
                                    prog.descriptor))  # fmt: skip
    return made, refused


def run(root: pathlib.Path, cache: pathlib.Path) -> dict[str, str]:
    """Each generated program on ttsim: ``correct (rel e)``, ``wrong (rel e)`` or the run's error, by case."""
    made, _ = generated()
    folders: list[tuple[str, Case, pathlib.Path]] = []
    for name, (case, prog) in made.items():
        folder = prog.write(root / f"case{len(folders)}")
        arrays = {k: numpy.asarray(v, dtype=numpy.float32) for k, v in case.inputs.items() if numpy.ndim(v) > 0}
        for out, want in case.expected.items():  # a collective's host takes Y's shape from here
            arrays.setdefault(out, numpy.zeros(want.shape, numpy.float32))
        numpy.savez(folder / "inputs.npz", **arrays)  # type: ignore[arg-type]  # pyright: ignore[reportArgumentType] -- numpy types its keyword arrays as its own options
        folders.append((name, case, folder))
    verdicts = ttsim.run([folder for _, _, folder in folders], cache)
    found = {}
    for (name, case, folder), verdict in zip(folders, verdicts, strict=True):
        if verdict.error or not (folder / "got.npy").exists():
            found[name] = f"error: {verdict.error[:160]}"
            continue
        ((_, want),) = case.expected.items()
        worst = error(numpy.load(folder / "got.npy").reshape(want.shape), want)
        found[name] = f"{'correct' if worst <= case.tolerance else 'wrong'} (rel {worst:.2g})"
    return found


def main() -> int:
    made, refused = generated()
    found: dict[str, str] = {}
    if sys.argv[1:] == ["run"]:
        with tempfile.TemporaryDirectory(prefix="alloy_tensix_gate_") as tmp:
            found = run(pathlib.Path(tmp), ttsim.default_cache())
    print("| program | tensix |\n|---|---|")
    for name in [*made, *refused]:
        print(f"| {name} | {found.get(name, 'generated') if name in made else 'refused: ' + refused[name]} |")
    caught = all(found.get(name, "").startswith("wrong") for name in PLANTED)
    others = [v for k, v in found.items() if k not in PLANTED]
    return 0 if not found or (caught and all(v.startswith("correct") for v in others)) else 1


if __name__ == "__main__":
    sys.exit(main())
