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

import dace
import numpy
from dace import data, symbolic

from alloy import tilelower
from alloy.gate import Case, error
from alloy.softhiergen.gate.programs import all_cases
from alloy.tensixgen import collectives, ttsim
from alloy.tensixgen.backend import Refused
from alloy.tensixgen.split import Program, program
from alloy.tensixgen.tasks import LANES


def task_of(sdfg: dace.SDFG, name: str | None = None) -> dict[str, object]:
    """The eval-task form the split takes, read off the SDFG: its non-transient arrays that are read (in declaration
    order), the one it writes, map or reduce by that array's size; ``name`` (default: the SDFG's) names the task."""
    name = name or sdfg.name
    arrays = [k for k, v in sdfg.arrays.items() if not v.transient and isinstance(v, data.Array)]
    found = [(n, s) for s in sdfg.states() for n in s.data_nodes() if n.data in arrays]
    written = [a for a in arrays if any(n.data == a and s.in_degree(n) > 0 for n, s in found)]
    if not written:
        raise Refused(f"{name}: no output")
    read = {n.data for n, s in found if s.out_degree(n) > 0}
    inputs = [[array, 0.0, 1.0] for array in arrays if array in read]
    kind = "reduce" if len(written) == 1 and sdfg.arrays[written[0]].total_size == 1 else "map"
    output: str | list[str] = written[0] if len(written) == 1 else written
    return {"name": name, "inputs": inputs, "output": output, "kind": kind, "program": [name]}


def widths(sdfg: dace.SDFG) -> int | tuple[int, int]:
    """The vectorizer's tile: :data:`LANES` along the innermost dimension, or, when every array's rows are ``K`` < 1024
    elements long (``K`` dividing 1024), 1024 / ``K`` whole rows. Either way a tile is 1024 consecutive elements, the
    host's tile of the array read as (-1, 32)."""
    arrays = [d for d in sdfg.arrays.values() if not d.transient and isinstance(d, data.Array)]
    rows = {int(symbolic.evaluate(d.shape[-1], sdfg.constants)) for d in arrays if len(d.shape) > 1}
    if len(rows) == 1 and all(len(d.shape) > 1 for d in arrays):
        (k,) = rows
        if k < LANES and LANES % k == 0:
            return (LANES // k, k)
    return LANES


def lower(sdfg: dace.SDFG, scalars: dict[str, float], name: str | None = None) -> Program:
    """The Tensix program of ``sdfg`` for ttsim's tt-metal (v08): a collective's NoC kernel, or the shared front and the
    kernel split; ``scalars`` are the values of its scalar arguments. Raises :class:`Refused` (or DaCe's error) when
    the split does not take it."""
    task = task_of(sdfg, name)
    if (node := collectives.comm_node(sdfg)) is not None:
        return collectives.program(task, sdfg, node)
    tilelower.front(sdfg, widths(sdfg), fuse_multiply_add=False)
    return program(task, sdfg, scalars, version="v08")


def lowered(case: Case) -> Program:
    """The case's Tensix program through :func:`alloy.tilelower.lower`."""
    scalars = {name: float(value) for name, value in case.inputs.items() if numpy.ndim(value) == 0}
    return tilelower.lower(case.sdfg(), "tensix", scalars, case.name)


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
        several = len(case.expected) > 1  # the host saves each output as got_<name>.npy
        files = {out: folder / (f"got_{out}.npy" if several else "got.npy") for out in case.expected}
        if verdict.error or not all(f.exists() for f in files.values()):
            found[name] = f"error: {verdict.error[:160]}"
            continue
        worst = max(error(numpy.load(files[out]).reshape(want.shape), want) for out, want in case.expected.items())
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
