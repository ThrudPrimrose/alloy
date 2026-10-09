# Copyright 2026 ETH Zurich and the Alloy authors.
"""``alloy build path/to/kernel.py:function --out dir``: outline, sweep, verify, time, and write the report."""

import argparse
import importlib.util
import pathlib

from dace.frontend.python.parser import DaceProgram

from alloy import configuration_matrix, machine, report
from alloy.backend import sweep
from alloy.evaluate import timing, verify
from alloy.evaluate.link import Linker
from alloy.frontend import inputs, regions


def load_program(spec: str) -> DaceProgram:
    """The ``@dace.program`` named by ``file.py:function``."""
    path, _, name = spec.partition(":")
    module_spec = importlib.util.spec_from_file_location(pathlib.Path(path).stem, path)
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"cannot import {path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    program = vars(module)[name]
    if not isinstance(program, DaceProgram):
        raise TypeError(f"{spec} is not a @dace.program")
    return program


def main() -> None:
    parser = argparse.ArgumentParser(prog="alloy")
    sub = parser.add_subparsers(dest="command", required=True)
    build_cmd = sub.add_parser("build", help="outline a program and build every region candidate")
    build_cmd.add_argument("program", help="file.py:function")
    build_cmd.add_argument("--out", type=pathlib.Path, required=True)
    build_cmd.add_argument(
        "--matrix",
        type=pathlib.Path,
        default=configuration_matrix.DEFAULT_PATH,
        help="configuration matrix TOML (default: the one shipped in the alloy package)",
    )
    build_cmd.add_argument(
        "--finite-inputs",
        action="store_true",
        help="declare that no input is NaN or Inf, which opens FP levels that need it (fast)",
    )
    build_cmd.add_argument(
        "--manifest",
        type=pathlib.Path,
        help="HPCAgent-Bench style manifest (sizes, fuzzed ranges, inputs); default: kernel.yaml next to kernel.py. "
        "Without one, candidates are built but not verified.",
    )
    build_cmd.add_argument("--iterations", type=int, default=2, help="fuzz draws every candidate is verified on")
    args = parser.parse_args()
    machine.limit_memory(0.75)
    matrix = configuration_matrix.load(args.matrix)
    program = regions.outline(load_program(args.program), matrix.libm_calls)
    args.out.mkdir(parents=True, exist_ok=True)
    reports = sweep.run(program, matrix, args.out, finite_inputs=args.finite_inputs)
    path, _, function = args.program.partition(":")
    manifest_path = args.manifest or inputs.manifest_for(pathlib.Path(path))
    verification, timings = None, None
    if manifest_path.is_file():
        manifest = inputs.load(manifest_path, function)
        cases = verify.Cases([inputs.draw(manifest, i) for i in range(args.iterations)], manifest.outputs)
        verification = verify.verify(program, matrix, reports, cases, args.out)
        timings = timing.time_program(Linker(program, matrix, args.out), reports, verification, manifest)
    else:
        print(f"no manifest at {manifest_path}: candidates are built, not verified or timed")
    report.write(reports, matrix, args.out, verification, timings)
    print(f"{len(reports)} regions -> {args.out / 'report.md'}")


if __name__ == "__main__":
    main()
