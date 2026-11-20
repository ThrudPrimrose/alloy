# Copyright 2026 ETH Zurich and the Alloy authors.
"""The eval tasks' tile programs: each task's bench kernel through the bench's canonical pipeline (what Alloy
receives), DaCe's vectorizer at one Tensix tile (1024 lanes), the sweep's placement on the task's arrays, and the
Tensix kernel split."""

import dace
from dace import placement
from dace.symbolic import int_floor
from dace.transformation.passes.vectorization.config import VectorizeConfig
from dace.transformation.passes.vectorization.enums import ISA
from dace.transformation.passes.vectorization.vectorize_cpu_multi_dim import VectorizeCPUMultiDim

from alloy.tensixgen.backend import Refused
from alloy.tensixgen.split import INTERLEAVED, SHARDED, TILES, Options, Program, program

__all__ = ["LANES", "place", "programs", "tile_sdfg"]

#: One Tensix tile, 32 x 32 elements.
LANES = 1024
#: The DRAM banks interleaved pages are dealt over: the host's device decides.
BANKS = dace.symbol("NB")


def tile_sdfg(name: str) -> tuple[dace.SDFG, dict[str, float]]:
    """Bench kernel ``name`` vectorized to tile nodes of one Tensix tile, and its numeric scalars (the bench's init)."""
    from hpcagent_bench.precision import Precision
    from hpcagent_bench.spec import KERNELS, BenchSpec

    from alloy.hb_plugin.adapter import pipeline_sdfg

    full = next(k for k in KERNELS if k.rsplit("/", 1)[-1] == name)
    spec = BenchSpec.load(full)
    sdfg = pipeline_sdfg(spec, "canon_cpu", Precision.FP32)
    # the ISA only names the CPU fallback; every compute tile node is set to ``tensix`` afterwards (backend.use_tensix)
    config = VectorizeConfig(widths=(LANES,), target_isa=ISA.SCALAR, assume_even=True)
    VectorizeCPUMultiDim(config).apply_pass(sdfg, {})
    init = spec.init.scalars if spec.init else {}
    return sdfg, {k: float(v) for k, v in init.items() if isinstance(v, int | float) and not isinstance(v, bool)}


def place(desc: dace.data.Data, kind: str, cores: int) -> placement.Placement:
    """The placement of ``kind`` for ``desc``: interleaved deals one tile per page round-robin over the DRAM banks
    (a 1-D array's tile is 1024 consecutive elements, a 2-D array's 32 x 32), sharded gives each of ``cores`` cores
    one block of the outermost dimension (height sharding)."""
    shape = desc.shape
    if len(shape) not in (1, 2):
        raise Refused(f"a {len(shape)}-D array: the sweep places 1-D and 2-D arrays")
    if kind == SHARDED:
        rows = int_floor(shape[0], cores)
        if len(shape) == 1:
            return placement.Placement(cores, placement.SymbolicLambda(lambda i: (i // rows) % cores))
        return placement.Placement(cores, placement.SymbolicLambda(lambda i, j: (i // rows) % cores))
    if len(shape) == 1:
        return placement.Placement(BANKS, placement.SymbolicLambda(lambda i: (i // LANES) % BANKS))
    per_row = int_floor(shape[1], 32)
    return placement.Placement(BANKS, placement.SymbolicLambda(lambda i, j: ((i // 32) * per_row + j // 32) % BANKS))


def programs(tasks: list[dict], options: Options = Options(), version: str = "v06") -> list[Program]:
    """The tile program of each eval task (``agents/tasks.json``'s form), its arrays placed as ``options`` says; a
    reduction's output stays in DRAM, where each core writes its partial tile."""
    if options.placement == SHARDED and not (options.cores and TILES % options.cores == 0):
        raise Refused(f"a sharded placement needs the cores, a divisor of {TILES}; given {options.cores}")
    out = []
    for task in tasks:
        sdfg, scalars = tile_sdfg(str(task["name"]))
        inputs = [str(name) for name, *_ in task["inputs"]]
        for name in dict.fromkeys([*inputs, str(task["output"])]):
            desc = sdfg.arrays[name]
            if isinstance(desc, dace.data.Array):  # the split refuses any other
                kind = options.placement if name in inputs or task["kind"] != "reduce" else INTERLEAVED
                desc.placement = place(desc, kind, options.cores)
        out.append(program(task, sdfg, scalars, options, version))
    return out
