# Copyright 2026 ETH Zurich and the Alloy authors.
"""The eval tasks' tile programs: each task's bench kernel through the bench's canonical pipeline (what Alloy
receives), DaCe's vectorizer at one Tensix tile (1024 lanes), and the Tensix kernel split."""

import dace
from dace.transformation.passes.vectorization.config import VectorizeConfig
from dace.transformation.passes.vectorization.enums import ISA
from dace.transformation.passes.vectorization.vectorize_cpu_multi_dim import VectorizeCPUMultiDim

from alloy.tensixgen.split import Options, Program, program

__all__ = ["LANES", "programs", "tile_sdfg"]

#: One Tensix tile, 32 x 32 elements.
LANES = 1024


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


def programs(tasks: list[dict], options: Options = Options(), version: str = "v06") -> list[Program]:
    """The tile program of each eval task (``agents/tasks.json``'s form)."""
    out = []
    for task in tasks:
        sdfg, scalars = tile_sdfg(str(task["name"]))
        out.append(program(task, sdfg, scalars, options, version))
    return out
