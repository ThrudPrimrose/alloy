# Copyright 2026 ETH Zurich and the Alloy authors.
"""Program inputs from an HPCAgent-Bench manifest (``parameters`` presets with a ``fuzzed`` range, ``args``), drawn by
the bench's fuzzer and initializer; a manifest outside the corpus names its kernel as ``file.py:function``."""

import importlib.util
import pathlib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

import dace
import numpy as np
import pydantic.dataclasses
from dace.sdfg import nodes

from alloy.frontend import scopes
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
    """A manifest as the bench reads it (``raw`` YAML, ``spec``), its output arguments and the dtype inputs are drawn
    at. ``spec``'s annotation resolves in :func:`load`, after the bench is imported."""

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
    """Parse the manifest with the bench's reader; inputs are drawn at ``datatype``. Outside the corpus, ``program``
    (``file.py:function``) names the kernel whose signature orders the inputs."""
    require_bench()
    from hpcagent_bench import paths  # noqa: PLC0415 -- alloy never loads the bench at import time
    from hpcagent_bench.spec import BenchSpec, KernelSite, load_yaml  # noqa: PLC0415

    raw = load_yaml(path.read_text())
    if path.resolve().is_relative_to(paths.BENCHMARKS.resolve()):
        spec = BenchSpec.from_yaml(raw, source=str(path))
    elif program is None:
        raise ValueError(f"{path} is outside the bench corpus: name its kernel as file.py:function")
    else:
        file, _, function = program.partition(":")
        reference = pathlib.Path(file).resolve()
        site = KernelSite(
            short_name=path.stem, relative_path=str(reference.parent), module_name=reference.stem, func_name=function
        )
        spec = BenchSpec.from_dict(raw, site, str(path))
    # cast: pydantic expects its internal dataclass protocol, which the decorator does not declare
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
    """Inputs at fixed ``sizes``: a corpus kernel's through the bench's dispatch (its own ``initialize`` if any),
    else the auto-initializer."""
    from hpcagent_bench import paths  # noqa: PLC0415
    from hpcagent_bench.categories import Preset  # noqa: PLC0415
    from hpcagent_bench.frameworks.benchmark import Benchmark  # noqa: PLC0415
    from hpcagent_bench.initialize import auto_initialize  # noqa: PLC0415
    from hpcagent_bench.precision import precision_from_datatype  # noqa: PLC0415

    spec = manifest.spec
    if spec.init is None:
        raise ValueError(f"{manifest.path}: no init block, so there are no inputs to draw")
    if manifest.path.resolve().is_relative_to(paths.BENCHMARKS.resolve()):
        data = Benchmark(spec.short_name).get_data(
            preset=Preset.FUZZED, datatype=manifest.datatype, input_seed=seed, params_override=sizes
        )
        return Draw(sizes=sizes, values={name: data[name] for name in spec.init.output_args})
    if spec.init.func_name:
        raise ValueError(f"{manifest.path}: a custom {spec.init.func_name}() is only called for a corpus kernel")
    values = auto_initialize(
        spec, Preset.FUZZED, precision_from_datatype(manifest.datatype), seed=seed, params_override=sizes
    )
    return Draw(sizes=sizes, values=dict(zip(spec.init.output_args, values, strict=True)))


def presets(manifest: Manifest) -> list[dict[str, int]]:
    """The manifest's fixed size presets (``S``, ``L``, ...), without the ``fuzzed`` ranges."""
    from hpcagent_bench.categories import Preset  # noqa: PLC0415

    return [dict(sizes) for name, sizes in manifest.raw["parameters"].items() if name != Preset.FUZZED.text]


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


#: Calls defined on only part of the reals: an input that may reach one has a domain only a manifest states.
DOMAIN_CALLS = frozenset(
    {"sqrt", "log", "log2", "log10", "log1p", "pow", "asin", "acos", "acosh", "atanh", "lgamma", "tgamma", "fmod"}
)
#: Sizes of the derived draws: odd, so a vector loop has a remainder, and different per draw.
DERIVED_SIZES = (37, 61)


def derived_outputs(sdfg: dace.SDFG) -> tuple[str, ...]:
    """The arguments ``sdfg`` writes (a non-transient written at its top level), in argument order."""
    written = {
        node.data
        for node, parent in sdfg.all_nodes_recursive()
        if isinstance(node, nodes.AccessNode)
        and isinstance(parent, dace.SDFGState)
        and parent.sdfg is sdfg
        and parent.in_degree(node) > 0
    }
    return tuple(name for name in sdfg.arglist() if name in written and not sdfg.arrays[name].transient)


def data_arguments(sdfg: dace.SDFG) -> dict[str, dace.data.Data]:
    """``sdfg``'s array and scalar arguments in argument order; a size symbol is no data, though ``arglist`` lists it
    as a scalar."""
    return {name: desc for name, desc in sdfg.arglist().items() if name not in sdfg.free_symbols}


def domain_gap(sdfg: dace.SDFG) -> str:
    """Why an input of ``sdfg`` may need values only a manifest knows, or ``""`` when any value is valid: a call
    defined on part of the reals, or an integer argument that is no size symbol (it may index)."""
    if calls := sorted(scopes.called_names(sdfg) & DOMAIN_CALLS):
        return f"calls {', '.join(calls)}"
    integers = [
        name for name, desc in data_arguments(sdfg).items() if np.issubdtype(desc.dtype.as_numpy_dtype(), np.integer)
    ]
    return f"integer argument {integers[0]}" if integers else ""


def derived_draw(sdfg: dace.SDFG, iteration: int) -> Draw:
    """One draw without a manifest: every size symbol at :data:`DERIVED_SIZES`, every array and scalar argument
    uniform in [0, 1) at its dtype, seeded by ``iteration``. Only valid for an ``sdfg`` without a :func:`domain_gap`."""
    size = DERIVED_SIZES[iteration % len(DERIVED_SIZES)]
    sizes = {name: size for name in sdfg.arglist() if name in sdfg.free_symbols}
    numeric: dict[dace.symbol | str, int | float] = {k: v for k, v in sizes.items()}  # noqa: C416 -- widens types
    rng = np.random.default_rng(iteration)
    values: dict[str, Any] = {}
    for name, desc in data_arguments(sdfg).items():
        dtype = desc.dtype.as_numpy_dtype()
        shape = tuple(int(dace.symbolic.evaluate(s, numeric)) for s in desc.shape)
        drawn = rng.random(shape) if isinstance(desc, dace.data.Array) else rng.random()
        values[name] = np.asarray(drawn).astype(dtype) if isinstance(desc, dace.data.Array) else dtype.type(drawn)
    return Draw(sizes=sizes, values=values)
