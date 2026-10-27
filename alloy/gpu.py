# Copyright 2026 ETH Zurich and the Alloy authors.
"""Speculative threadblock shapes for a GPU program's device maps. Every shape of a map's rank is rendered by CPF in
the device dialect and compiled for the device; each map then takes the shape its compiler report ranks first, and
nothing is run: no spills, then occupancy (counted only up to :data:`OCCUPANCY_SATURATION`, past which latency is
hidden), then an innermost dimension of at least a warp (coalesced accesses), then fewer registers.

A map's roofline time (its work and traffic) is the same for every shape, so it orders maps, never the shapes of one
map; the compiler's register, spill and shared-memory counts are what a shape changes."""

import re
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import dace
from dace import symbolic
from dace.codegen import cpf
from dace.sdfg import nodes

__all__ = [
    "Pick",
    "Shape",
    "SmLimits",
    "Usage",
    "blocks",
    "candidate_shapes",
    "cuda_occupancy",
    "device_maps",
    "hip_usage",
    "nvcc_usage",
    "speculate",
]

Shape = tuple[int, int, int]
#: A rank-1 map's shapes, and a rank >= 2 map's (innermost dimension first, as ``gpu_block_size`` orders them).
SHAPES_1D: tuple[Shape, ...] = ((64, 1, 1), (128, 1, 1), (256, 1, 1), (512, 1, 1), (1024, 1, 1))
SHAPES_ND: tuple[Shape, ...] = ((32, 4, 1), (32, 8, 1), (16, 16, 1), (64, 4, 1), (32, 16, 1), (128, 2, 1))
#: Threads per warp (CUDA) or the narrowest wavefront (HIP): an innermost dimension below it splits a coalesced row.
WARP = 32
#: The occupancy past which more warps hide no more latency; above it shapes tie on occupancy.
OCCUPANCY_SATURATION = 0.5
#: Block sizes no candidate has as its thread count, one per device map of a probe run: a map's block tells its
#: ordinal, and its kernel's ``__launch_bounds__`` the kernel's name.
PROBE_THREADS: tuple[int, ...] = tuple(32 * m for m in range(3, 32) if m not in (4, 8, 16))


@dataclass(frozen=True, slots=True)
class SmLimits:
    """One streaming multiprocessor of a compute capability: what bounds how many blocks reside on it."""

    threads: int
    blocks: int
    shared_bytes: int
    registers: int = 65536


#: Per compute capability (CUDA C Programming Guide, technical specifications per compute capability).
SM_LIMITS: dict[str, SmLimits] = {
    "7.0": SmLimits(2048, 32, 96 * 1024),
    "7.5": SmLimits(1024, 16, 64 * 1024),
    "8.0": SmLimits(2048, 32, 164 * 1024),
    "8.6": SmLimits(1536, 16, 100 * 1024),
    "8.7": SmLimits(1536, 16, 164 * 1024),
    "8.9": SmLimits(1536, 24, 100 * 1024),
    "9.0": SmLimits(2048, 32, 228 * 1024),
    "10.0": SmLimits(2048, 32, 228 * 1024),
    "12.0": SmLimits(1536, 32, 100 * 1024),
}
#: Registers are allocated per warp in units of this many.
REGISTER_UNIT = 256
#: Waves one SIMD holds at most, by AMD architecture family (``gfx9``: CDNA and Vega; later: RDNA).
MAX_WAVES = {"gfx9": 8, "gfx10": 16, "gfx11": 16, "gfx12": 16}


@dataclass(frozen=True, slots=True)
class Usage:
    """What the device compiler reports for one kernel; ``waves`` is HIP's own occupancy (waves per SIMD)."""

    registers: int
    spill_bytes: int
    shared_bytes: int
    waves: int | None = None


@dataclass(frozen=True, slots=True)
class Pick:
    """The shape a map takes and why: its usage there and the occupancy it reaches; ``ranked`` is every shape tried,
    best first."""

    shape: Shape
    usage: Usage
    occupancy: float
    ranked: tuple[tuple[Shape, Usage, float], ...]


def device_maps(sdfg: dace.SDFG) -> list[nodes.MapEntry]:
    """The GPU device maps of ``sdfg``, in a stable order a deep copy reproduces."""
    return [
        node
        for node, _ in sdfg.all_nodes_recursive()
        if isinstance(node, nodes.MapEntry) and node.map.schedule == dace.ScheduleType.GPU_Device
    ]


def candidate_shapes(entry: nodes.MapEntry, max_threads: int = 1024) -> list[Shape]:
    """The shapes a map is tried with: by its rank, without one wider than a constant extent of the map or larger than
    ``max_threads`` threads."""
    sizes = list(reversed(entry.map.range.size()))  # innermost first, like gpu_block_size
    extents = [None if symbolic.issymbolic(size) else int(size) for size in sizes]
    shapes = SHAPES_1D if len(entry.map.params) == 1 else SHAPES_ND

    def fits(shape: Shape) -> bool:
        within = all(e is None or s <= int(e) for s, e in zip(shape, extents))
        return within and shape[0] * shape[1] * shape[2] <= max_threads

    kept = [shape for shape in shapes if fits(shape)]
    return kept or [min(shapes, key=lambda s: s[0] * s[1] * s[2])]


NVCC_FUNCTION = re.compile(r"Compiling entry function '([^']+)'")
NVCC_SPILLS = re.compile(r"(\d+) bytes spill stores, (\d+) bytes spill loads")
NVCC_USED = re.compile(r"Used (\d+) registers(?:.*?, (\d+) bytes smem)?")


def nvcc_usage(report: str) -> dict[str, Usage]:
    """Every kernel's usage in ``nvcc -Xptxas -v`` output, by mangled name."""
    found: dict[str, Usage] = {}
    name, spills = "", 0
    for line in report.splitlines():
        if match := NVCC_FUNCTION.search(line):
            name, spills = match.group(1), 0
        elif match := NVCC_SPILLS.search(line):
            spills = int(match.group(1)) + int(match.group(2))
        elif (match := NVCC_USED.search(line)) and name:
            found[name] = Usage(int(match.group(1)), spills, int(match.group(2) or 0))
    return found


HIP_FIELD = re.compile(
    r"remark:\s+(Function Name|VGPRs Spill|SGPRs Spill|VGPRs|LDS Size \[bytes/block\]|Occupancy \[waves/SIMD\]): (\S+)"
)
#: Bytes one spilled register costs (a 32-bit lane).
REGISTER_BYTES = 4


def hip_usage(report: str) -> dict[str, Usage]:
    """Every kernel's usage in ``hipcc -Rpass-analysis=kernel-resource-usage`` output, by (mangled) name; a spilled
    register counts :data:`REGISTER_BYTES`."""
    fields: dict[str, dict[str, str]] = {}
    name = ""
    for line in report.splitlines():
        match = HIP_FIELD.search(line)
        if match is None:
            continue
        key, value = match.groups()
        if key == "Function Name":
            name = value
            fields[name] = {}
        elif name:
            fields[name][key] = value
    return {
        kernel: Usage(
            registers=int(f.get("VGPRs", 0)),
            spill_bytes=REGISTER_BYTES * (int(f.get("VGPRs Spill", 0)) + int(f.get("SGPRs Spill", 0))),
            shared_bytes=int(f.get("LDS Size [bytes/block]", 0)),
            waves=int(f["Occupancy [waves/SIMD]"]) if "Occupancy [waves/SIMD]" in f else None,
        )
        for kernel, f in fields.items()
    }


def cuda_occupancy(usage: Usage, threads: int, limits: SmLimits) -> float:
    """Resident warps over the SM's most, for blocks of ``threads`` threads with ``usage``."""
    warps = -(-threads // WARP)
    per_warp = -(-usage.registers * WARP // REGISTER_UNIT) * REGISTER_UNIT
    bounds = [limits.blocks, limits.threads // WARP // warps]
    if per_warp:
        bounds.append(limits.registers // (per_warp * warps))
    if usage.shared_bytes:
        bounds.append(limits.shared_bytes // usage.shared_bytes)
    return min(bounds) * warps / (limits.threads // WARP)


def occupancy(usage: Usage, shape: Shape, dialect: str, arch: str) -> float:
    if dialect == "hip":
        digits = arch.removeprefix("gfx")
        most = MAX_WAVES.get(f"gfx{digits[:2] if len(digits) >= 4 else digits[:1]}", 8)
        return (usage.waves or 0) / most
    return cuda_occupancy(usage, shape[0] * shape[1] * shape[2], SM_LIMITS[arch])


def rank_key(shape: Shape, usage: Usage, reached: float) -> tuple[bool, int, float, bool, int]:
    return (
        usage.spill_bytes > 0,
        usage.spill_bytes,
        -min(reached, OCCUPANCY_SATURATION),
        shape[0] < WARP,
        usage.registers,
    )


def compile_usage(device_code: str, dialect: str, arch: str) -> dict[str, Usage]:
    """Compile a CPF device unit for ``arch`` (no device needed) and read every kernel's usage."""
    with tempfile.TemporaryDirectory(prefix="alloy_gpu_") as folder:
        unit = Path(folder) / f"unit.{'cu' if dialect == 'cuda' else 'hip'}"
        unit.write_text(device_code)
        if dialect == "cuda":
            argv = ["nvcc", *cpf.CUDA_BUILD_FLAGS, f"-arch=sm_{arch.replace('.', '')}", "-Xptxas", "-v"]
        else:
            argv = ["hipcc", "-std=c++20", f"--offload-arch={arch}", "-Rpass-analysis=kernel-resource-usage"]
        done = subprocess.run(
            [*argv, "-c", str(unit), "-o", str(unit.with_suffix(".o"))], capture_output=True, text=True, check=False
        )
        if done.returncode:
            raise RuntimeError(f"{argv[0]} refused a CPF device unit:\n{done.stderr[-4000:]}")
        return (nvcc_usage if dialect == "cuda" else hip_usage)(done.stdout + done.stderr)


#: Runs the program's GPU pipeline with each device map of ``ordinal`` given ``shape`` (through :func:`blocks`) and
#: returns the SDFG it produces.
Pipeline = Callable[[dict[int, Shape]], dace.SDFG]


def blocks(shapes: dict[int, Shape]) -> Callable[[dace.SDFG], None]:
    """The bench pipeline's ``offloaded`` hook giving device map ``ordinal`` the block ``shapes[ordinal]``, before the
    pipeline tiles the map by its block. A map's ordinal is its place, in walk order, among the device maps the
    pipeline chose a block for (a map holding a thread-block map has none)."""

    def set_blocks(sdfg: dace.SDFG) -> None:
        chosen = [entry for entry in device_maps(sdfg) if entry.map.gpu_block_size is not None]
        for ordinal, shape in shapes.items():
            if ordinal < len(chosen):
                chosen[ordinal].map.gpu_block_size = list(shape)

    return set_blocks


def device_code(sdfg: dace.SDFG, dialect: str) -> str:
    return cpf.render(sdfg, language=dialect, check_compiles=False).device_code


@dataclass(frozen=True, slots=True)
class DeviceMap:
    """A device map of the pipeline's program: its map (rank and extents), its kernel's name and the block the
    pipeline picks for it."""

    entry: nodes.MapEntry
    kernel: str
    default: Shape


def identified(pipeline: Pipeline, dialect: str) -> dict[int, DeviceMap]:
    """Every device map by ordinal, found by running the pipeline with one :data:`PROBE_THREADS` size per ordinal, in
    batches until a batch finds no map; its default block is the one the pipeline picks at the same place."""
    defaults = [tuple(entry.map.gpu_block_size or (0, 0, 0)) for entry in device_maps(pipeline({}))]
    found: dict[int, DeviceMap] = {}
    first = 0
    while True:
        probes = {first + i: (threads, 1, 1) for i, threads in enumerate(PROBE_THREADS)}
        sdfg = pipeline(probes)
        code = device_code(sdfg, dialect)
        place = {
            entry.map.gpu_block_size[0]: (i, entry)
            for i, entry in enumerate(device_maps(sdfg))
            if entry.map.gpu_block_size
        }
        batch = 0
        for ordinal, (threads, _, _) in probes.items():
            kernel = re.search(rf"__launch_bounds__\({threads}\)\s+(\w+)\s*\(", code)
            if threads in place and kernel is not None:
                i, entry = place[threads]
                default = defaults[i] if i < len(defaults) else (0, 0, 0)
                found[ordinal] = DeviceMap(entry, kernel.group(1), (default[0], default[1], default[2]))
                batch += 1
        if batch < len(PROBE_THREADS):
            return found
        first += len(PROBE_THREADS)


def kernel_usage(usages: dict[str, Usage], name: str) -> Usage | None:
    """``name``'s usage, whether the report spells it plain (HIP) or mangled (nvcc: ``_Z<len><name>...``)."""
    for kernel, usage in usages.items():
        if kernel == name or kernel.startswith(f"_Z{len(name)}{name}"):
            return usage
    return None


def speculate(pipeline: Pipeline, dialect: str, arch: str) -> tuple[dace.SDFG, dict[int, Pick]]:
    """Pick each device map's threadblock shape (see the module docstring) and return the program built with the
    picks, with the picks by ordinal; a map no shape could be measured for keeps the pipeline's own block.
    ``arch``: a compute capability (``"8.9"``) or a ``gfx`` target."""
    maps = identified(pipeline, dialect)
    # the pipeline's own block first: a shape replaces it only when the compiler report ranks it strictly better
    candidates = {
        ordinal: list(
            dict.fromkeys([m.default, *candidate_shapes(m.entry)] if min(m.default) > 0 else candidate_shapes(m.entry))
        )
        for ordinal, m in maps.items()
    }
    tried: dict[int, list[tuple[Shape, Usage, float]]] = {ordinal: [] for ordinal in maps}
    for shape in dict.fromkeys(s for shapes in candidates.values() for s in shapes):
        takers = {ordinal: shape for ordinal, shapes in candidates.items() if shape in shapes}
        usages = compile_usage(device_code(pipeline(takers), dialect), dialect, arch)
        for ordinal in takers:
            usage = kernel_usage(usages, maps[ordinal].kernel)
            if usage is not None:
                tried[ordinal].append((shape, usage, occupancy(usage, shape, dialect, arch)))
    picks = {
        ordinal: Pick(ranked[0][0], ranked[0][1], ranked[0][2], tuple(ranked))
        for ordinal, rows in tried.items()
        if (ranked := sorted(rows, key=lambda row: rank_key(*row)))
    }
    return pipeline({ordinal: pick.shape for ordinal, pick in picks.items()}), picks


def native_arch(dialect: str) -> str:
    """The compute capability (``nvidia-smi``) or ``gfx`` target (``amdgpu-arch``) of this machine's first device."""
    if dialect == "cuda":
        argv: Sequence[str] = ("nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader")
    else:
        argv = ("amdgpu-arch",)
    done = subprocess.run(argv, capture_output=True, text=True, check=True)
    return done.stdout.split()[0]
