# Copyright 2026 ETH Zurich and the Alloy authors.
"""Program inputs in the HPCAgent-Bench manifest format: ``parameters`` presets (with a ``fuzzed`` range for
speculative compiling) and an ``args`` block (shapes, outputs). Sizes are drawn by the bench's fuzzer under its
correctness cap and the arrays by its auto-initializer, so a corpus kernel's manifest works unchanged; a manifest
outside the corpus names its kernel as ``file.py:function``."""

import importlib.util
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import dace
import pydantic.dataclasses

from alloy.records import FOREIGN_RECORD, Strings, constructed

if TYPE_CHECKING:
    from hpcagent_bench.spec import BenchSpec


@dataclass(slots=True, frozen=True)
class Draw:
    """One fuzz iteration: the sizes and every input array/scalar by name."""

    sizes: dict[str, int]
    values: dict[str, Any]


@pydantic.dataclasses.dataclass(slots=True, frozen=True, config=FOREIGN_RECORD)
class Manifest:
    """A manifest read by the bench's reader: ``raw`` is the YAML as read, ``spec`` the bench's view of it,
    ``outputs`` the output arguments, and ``datatype`` the numpy dtype name the inputs are drawn at. The ``spec``
    annotation resolves in :func:`load`, after the bench is imported."""

    path: pathlib.Path
    raw: dict[str, Any]
    spec: "BenchSpec"
    outputs: Strings
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
    # cast: pydantic types the argument as its internal PydanticDataclass protocol, which the decorator does not
    # declare on the class
    pydantic.dataclasses.rebuild_dataclass(cast("Any", Manifest), _types_namespace={"BenchSpec": BenchSpec})
    return constructed(Manifest, path, path=path, raw=raw, spec=spec, outputs=spec.output_args, datatype=datatype)


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
    """Inputs at fixed ``sizes``: a corpus kernel's through the bench's own dispatch (its ``initialize`` when the
    module defines one, which fixes dtypes the run precision does not, e.g. complex128), else the auto-initializer."""
    from hpcagent_bench import fuzz, paths  # noqa: PLC0415
    from hpcagent_bench.frameworks.benchmark import Benchmark  # noqa: PLC0415
    from hpcagent_bench.initialize import auto_initialize  # noqa: PLC0415
    from hpcagent_bench.precision import precision_from_datatype  # noqa: PLC0415

    spec = manifest.spec
    if spec.init is None:
        raise ValueError(f"{manifest.path}: no init block, so there are no inputs to draw")
    if manifest.path.resolve().is_relative_to(paths.BENCHMARKS.resolve()):
        data = Benchmark(spec.short_name).get_data(
            preset=fuzz.FUZZED_PRESET, datatype=manifest.datatype, input_seed=seed, params_override=sizes
        )
        return Draw(sizes=sizes, values={name: data[name] for name in spec.init.output_args})
    if spec.init.func_name:
        raise ValueError(f"{manifest.path}: a custom {spec.init.func_name}() is only called for a corpus kernel")
    values = auto_initialize(
        spec, fuzz.FUZZED_PRESET, precision_from_datatype(manifest.datatype), seed=seed, params_override=sizes
    )
    return Draw(sizes=sizes, values=dict(zip(spec.init.output_args, values, strict=True)))


def presets(manifest: Manifest) -> list[dict[str, int]]:
    """The manifest's fixed size presets (``S``, ``L``, ...), without the ``fuzzed`` ranges."""
    return [dict(sizes) for name, sizes in manifest.raw["parameters"].items() if name != "fuzzed"]


def constrained(manifest: Manifest, sizes: dict[str, int]) -> dict[str, int] | None:
    """``sizes`` snapped to the manifest's divisibility constraints, or ``None`` when a constraint still fails."""
    from hpcagent_bench import fuzz  # noqa: PLC0415

    snapped: dict[str, Any] = dict(sizes)
    fuzz.snap_divisible(snapped, manifest.spec.constraints)
    if not all(fuzz.safe_eval(c, snapped) for c in manifest.spec.constraints):
        return None
    return snapped


def largest_array(manifest: Manifest, sdfg: dace.SDFG) -> int:
    """Element count of the largest array of ``sdfg`` over the manifest's size presets: what a flat index reaches."""
    return max(
        (
            int(dace.symbolic.evaluate(d.total_size, {**sizes}))
            for sizes in presets(manifest)
            for d in sdfg.arrays.values()
        ),
        default=0,
    )
