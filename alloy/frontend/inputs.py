# Copyright 2026 ETH Zurich and the Alloy authors.
"""Program inputs in the HPCAgent-Bench manifest format: ``parameters`` presets (with a ``fuzzed`` range for
speculative compiling), ``init.arrays`` / ``init.scalars``, ``input_args`` and ``output_args``. Sizes are drawn by
the bench's fuzzer under its correctness cap and the arrays by its auto-initializer, so a corpus kernel's manifest
works unchanged."""

import pathlib
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class Draw:
    """One fuzz iteration: the sizes and every input array/scalar by name."""

    sizes: dict[str, int]
    values: dict[str, Any]


@dataclass(slots=True, frozen=True)
class Manifest:
    path: pathlib.Path
    raw: dict[str, Any]
    outputs: tuple[str, ...]


def manifest_for(program_file: pathlib.Path) -> pathlib.Path:
    """The manifest next to ``program_file``: ``kernel.py`` -> ``kernel.yaml``."""
    return program_file.with_suffix(".yaml")


def load(path: pathlib.Path, function: str) -> Manifest:
    """Read the manifest and fill the bench's bookkeeping fields from the program it describes."""
    from hpcagent_bench.spec import load_yaml  # noqa: PLC0415 -- alloy never loads the bench at import time

    raw = load_yaml(path.read_text())
    identity = {"short_name": path.stem, "relative_path": str(path.parent), "module_name": path.stem}
    raw = {**identity, "func_name": function, **raw}
    return Manifest(path=path, raw=raw, outputs=tuple(raw["output_args"]))


def draw(manifest: Manifest, iteration: int, datatype: str = "float64") -> Draw:
    """Sizes from the ``fuzzed`` ranges (capped for correctness), then inputs from the bench initializer, both seeded
    by ``iteration``."""
    from hpcagent_bench import fuzz  # noqa: PLC0415
    from hpcagent_bench.spec import BenchSpec  # noqa: PLC0415

    spec = BenchSpec.from_dict(manifest.raw, source=str(manifest.path))
    sizes = fuzz.sample_params(
        manifest.raw["parameters"],
        iteration,
        configs=spec.config_space,
        constraints=spec.constraints,
        size_cap=fuzz.correctness_size_cap(),
        config_names=spec.config_names,
    )
    ints: dict[str, int] = {}
    for name, value in sizes.items():
        if not isinstance(value, int | float):
            raise TypeError(f"{manifest.path}: parameter {name} drew {value!r}, not a size")
        ints[name] = int(value)
    return at(manifest, ints, iteration, datatype)


def at(manifest: Manifest, sizes: dict[str, int], seed: int = 0, datatype: str = "float64") -> Draw:
    """Inputs from the bench initializer at fixed ``sizes``."""
    from hpcagent_bench import fuzz  # noqa: PLC0415
    from hpcagent_bench.initialize import auto_initialize  # noqa: PLC0415
    from hpcagent_bench.precision import precision_from_datatype  # noqa: PLC0415
    from hpcagent_bench.spec import BenchSpec  # noqa: PLC0415

    spec = BenchSpec.from_dict(manifest.raw, source=str(manifest.path))
    if spec.init is None:
        raise ValueError(f"{manifest.path}: no init block, so there are no inputs to draw")
    values = auto_initialize(
        spec, fuzz.FUZZED_PRESET, precision_from_datatype(datatype), seed=seed, params_override=sizes
    )
    return Draw(sizes=sizes, values=dict(zip(spec.init.output_args, values, strict=True)))


def presets(manifest: Manifest) -> list[dict[str, int]]:
    """The manifest's fixed size presets (``S``, ``L``, ...), without the ``fuzzed`` ranges."""
    return [dict(sizes) for name, sizes in manifest.raw["parameters"].items() if name != "fuzzed"]
