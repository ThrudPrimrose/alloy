# Copyright 2026 ETH Zurich and the Alloy authors.
"""Program inputs in the HPCAgent-Bench manifest format: ``parameters`` presets (with a ``fuzzed`` range for
speculative compiling) and an ``args`` block (shapes, outputs). Sizes are drawn by the bench's fuzzer under its
correctness cap and the arrays by its auto-initializer, so a corpus kernel's manifest works unchanged; a manifest
outside the corpus names its kernel as ``file.py:function``."""

import importlib.util
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hpcagent_bench.spec import BenchSpec


@dataclass(slots=True, frozen=True)
class Draw:
    """One fuzz iteration: the sizes and every input array/scalar by name."""

    sizes: dict[str, int]
    values: dict[str, Any]


@dataclass(slots=True, frozen=True)
class Manifest:
    path: pathlib.Path
    raw: dict[str, Any]
    spec: "BenchSpec"
    outputs: tuple[str, ...]
    datatype: str


def require_bench() -> None:
    """Manifest inputs and the tolerance band live in HPCAgent-Bench, an optional extra of Alloy."""
    if importlib.util.find_spec("hpcagent_bench") is None:
        raise ImportError("manifest inputs and the tolerance band need HPCAgent-Bench: install alloy[bench]")


def load(path: pathlib.Path, program: str | None = None, datatype: str = "float64") -> Manifest:
    """Parse the manifest with the bench's own reader (``args`` block, derived identity); inputs are drawn at
    ``datatype``. A manifest outside the bench corpus names its kernel by ``program`` (``file.py:function``), whose
    signature orders the inputs."""
    require_bench()
    from hpcagent_bench import paths  # noqa: PLC0415 -- alloy never loads the bench at import time
    from hpcagent_bench.spec import BenchSpec, expand_args, load_yaml  # noqa: PLC0415

    raw = load_yaml(path.read_text())
    if path.resolve().is_relative_to(paths.BENCHMARKS.resolve()):
        spec = BenchSpec.from_yaml(raw, source=str(path))
    elif program is None:
        raise ValueError(f"{path} is outside the bench corpus: name its kernel as file.py:function")
    else:
        file, _, function = program.partition(":")
        reference = pathlib.Path(file).resolve()
        identity = {"short_name": path.stem, "name": path.stem, "module_name": reference.stem, "func_name": function}
        expanded = {**identity, "relative_path": str(reference.parent), **raw}
        expand_args(expanded, None, str(path))
        spec = BenchSpec.from_dict(expanded, str(path))
    return Manifest(path=path, raw=raw, spec=spec, outputs=spec.output_args, datatype=datatype)


def draw(manifest: Manifest, iteration: int) -> Draw:
    """Sizes from the ``fuzzed`` ranges (capped for correctness), then inputs from the bench initializer, both seeded
    by ``iteration``."""
    from hpcagent_bench import fuzz  # noqa: PLC0415

    spec = manifest.spec
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
    return at(manifest, ints, iteration)


def at(manifest: Manifest, sizes: dict[str, int], seed: int = 0) -> Draw:
    """Inputs from the bench initializer at fixed ``sizes``."""
    from hpcagent_bench import fuzz  # noqa: PLC0415
    from hpcagent_bench.initialize import auto_initialize  # noqa: PLC0415
    from hpcagent_bench.precision import precision_from_datatype  # noqa: PLC0415

    spec = manifest.spec
    if spec.init is None:
        raise ValueError(f"{manifest.path}: no init block, so there are no inputs to draw")
    values = auto_initialize(
        spec, fuzz.FUZZED_PRESET, precision_from_datatype(manifest.datatype), seed=seed, params_override=sizes
    )
    return Draw(sizes=sizes, values=dict(zip(spec.init.output_args, values, strict=True)))


def presets(manifest: Manifest) -> list[dict[str, int]]:
    """The manifest's fixed size presets (``S``, ``L``, ...), without the ``fuzzed`` ranges."""
    return [dict(sizes) for name, sizes in manifest.raw["parameters"].items() if name != "fuzzed"]
