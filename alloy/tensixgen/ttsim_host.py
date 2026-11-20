# Copyright 2026 ETH Zurich and the Alloy authors.
"""Runs generated Tensix programs (alloy.tensixgen) on a device ttnn opens (ttsim through TT_METAL_SIMULATOR, or a
card) under the eval contract v2 of alloy-tenstorrent ``agents/SPEC.md``, and prints one JSON verdict per program.
Standalone: it runs inside a tt-metal image and never imports alloy. Inputs, reference
and verdict are agents/host.py's ``task_run``: seeded float32 inputs over each input's range, the float64 program as
the reference, |got - ref| <= 1e-5 + 1e-3 |ref|, and a sum's partial tiles added in float64 with the allowance
2^-23 sqrt(N) |ref|. Its cores are the descriptor's (``options.cores``, 0 the whole grid), and each array lies where
the descriptor's ``placement`` says: interleaved DRAM, or L1 height sharded over those cores.

    python3 ttsim_host.py FOLDER...   # each: reader.cpp, compute.cpp, writer.cpp, config.json, program.json
"""

import json
import math
import pathlib
import sys
import traceback
from collections.abc import Callable
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import torch
    import ttnn  # pyright: ignore[reportMissingImports] -- only inside the tt-metal image

TILES = 1024
OUT_CB = 16
FP32_EPS = 2.0**-23
#: A JSON object as program.json and config.json hold it.
Json = dict[str, Any]
CALLS = ("exp", "log", "sqrt", "sin", "cos", "tanh", "abs")


def evaluate(
    program: list[str], arrays: dict[str, "torch.Tensor"], calls: dict[str, Callable[..., "torch.Tensor"]]
) -> "torch.Tensor":
    scope: dict[str, object] = {**calls, **arrays}
    target = ""
    for line in program:
        target, expression = line.split(" = ", 1)
        scope[target] = eval(expression, {"__builtins__": {}}, scope)
    return cast("torch.Tensor", scope[target])


def operands(task: Json) -> tuple[list["torch.Tensor"], "torch.Tensor"]:
    """host.py's ``task_operands``: the same seed, draw and float64 reference."""
    import torch

    g = torch.Generator().manual_seed(1234)
    shape = (TILES * 32, 32)
    xs = [(torch.rand(shape, generator=g, dtype=torch.float64) * (hi - lo) + lo).float().double()
          for _, lo, hi in task["inputs"]]  # fmt: skip
    calls = {name: getattr(torch, name) for name in CALLS} | {"sum": torch.sum, "max": torch.max}
    return xs, evaluate(task["program"], {n: x for (n, *_), x in zip(task["inputs"], xs)}, calls)


def verdict_of(task: Json, got: "torch.Tensor", want: "torch.Tensor") -> Json:
    """host.py's ``verdict_of``."""
    import torch

    got, want = got.double().flatten(), torch.as_tensor(want, dtype=torch.float64).flatten()
    rtol = 1e-3
    if task["reduce"] == "add":
        got = got.sum().reshape(1)
        rtol += FP32_EPS * math.sqrt(TILES * 32 * 32)
    diff = (got - want).abs()
    excess = (diff - (1e-5 + rtol * want.abs())).max().item()
    err = (diff / want.abs().clamp_min(1e-30)).max().item()
    return {"ok": bool(math.isfinite(excess) and excess <= 0), "err": err, "abs": diff.max().item()}


def unpack_mode(module: ModuleType) -> "type[ttnn.UnpackToDestMode]":
    """``UnpackToDestMode``: tt-metal 0.6x binds it only in the program-descriptor module (tensix_harness.py)."""
    try:
        return cast("type[ttnn.UnpackToDestMode]", module.UnpackToDestMode)
    except AttributeError:
        return cast("type[ttnn.UnpackToDestMode]", module._ttnn.program_descriptor.UnpackToDestMode)


def source_code(module: ModuleType) -> "ttnn.SourceType":
    """The inline-source kernel type: nested in ``KernelDescriptor`` in 0.8x, a module enum in 0.6x."""
    try:
        return cast("ttnn.SourceType", module.KernelDescriptor.SourceType.SOURCE_CODE)
    except AttributeError:
        return cast("ttnn.SourceType", module._ttnn.program_descriptor.SourceType.SOURCE_CODE)


def per_core(module: ModuleType, values: dict[tuple[int, int], list[int]]) -> object:
    """Runtime arguments per core (x, y): ``RuntimeArgs`` in tt-metal 0.8x, nested lists ``[x][y]`` in 0.6x."""
    gx, gy = max(x for x, _ in values) + 1, max(y for _, y in values) + 1
    try:
        args = module.RuntimeArgs()
    except AttributeError:
        return [[values.get((x, y), []) for y in range(gy)] for x in range(gx)]
    for (x, y), v in values.items():
        args[x][y] = v
    return args


def run(dev: "ttnn.MeshDevice", folder: pathlib.Path) -> Json:
    import ttnn  # pyright: ignore[reportMissingImports] -- only inside the tt-metal image

    task = json.loads((folder / "program.json").read_text())
    cfg = json.loads((folder / "config.json").read_text())
    xs, want = operands(task)
    grid = dev.compute_with_storage_grid_size()
    cores = [(x, y) for y in range(grid.y) for x in range(grid.x)]  # core index = y * grid.x + x
    cores = cores[: task["options"]["cores"] or len(cores)]
    assert len(cores) <= TILES, f"{len(cores)} cores for {TILES} tiles: a core without a tile hangs"
    core = ttnn.CoreRangeSet([ttnn.CoreRange(ttnn.CoreCoord(x, y), ttnn.CoreCoord(x, y)) for x, y in cores])
    placed = task["placement"]

    def memory(name: str) -> "ttnn.MemoryConfig":
        """DRAM interleaved, or L1 height sharded: ``tiles`` tile rows on each core, shard k on core k."""
        if placed[name]["kind"] == "interleaved":
            return ttnn.DRAM_MEMORY_CONFIG
        assert placed[name]["cores"] == len(cores), f"{name} is sharded over {placed[name]['cores']} cores"
        spec = ttnn.ShardSpec(core, [32 * placed[name]["tiles"], 32], ttnn.ShardOrientation.ROW_MAJOR)
        return ttnn.MemoryConfig(ttnn.TensorMemoryLayout.HEIGHT_SHARDED, ttnn.BufferType.L1, spec)

    names = [name for name, *_ in task["inputs"]]
    tensors = [ttnn.from_torch(x.float(), dtype=ttnn.float32, layout=ttnn.TILE_LAYOUT, device=dev,
                               memory_config=memory(name)) for name, x in zip(names, xs)]  # fmt: skip
    reduce = bool(task["reduce"])
    out_shape = [32 * len(cores), 32] if reduce else list(xs[0].shape)
    out_mem = memory(task["output"])
    out = ttnn.allocate_tensor_on_device(ttnn.Shape(out_shape), ttnn.float32, ttnn.TILE_LAYOUT, dev, out_mem)
    plan = dict.fromkeys(range(len(xs)), (2, "float32")) | {OUT_CB: (2, "float32")}
    for extra in cfg.get("extra_cbs", []):
        plan[int(extra["index"])] = (int(extra["tiles"]), extra["format"])
    fmt = {"float32": (ttnn.float32, 4096), "bfloat16": (ttnn.bfloat16, 2048)}
    cbs = [
        ttnn.CBDescriptor(total_size=tiles * fmt[f][1], core_ranges=core,
                          format_descriptors=[ttnn.CBFormatDescriptor(buffer_index=i, data_format=fmt[f][0], page_size=fmt[f][1])])
        for i, (tiles, f) in sorted(plan.items())
    ]  # fmt: skip
    config = ttnn.ComputeConfigDescriptor()
    config.fp32_dest_acc_en = bool(cfg["fp32_dest_acc_en"])
    config.math_approx_mode = bool(cfg["math_approx_mode"])
    config.math_fidelity = getattr(ttnn.MathFidelity, cfg["math_fidelity"])
    mode = unpack_mode(ttnn)
    modes = [mode.Default] * 64
    for i in cfg["unpack_to_dest_fp32"]:
        modes[int(i)] = mode.UnpackToDestFp32
    try:
        config.unpack_to_dest_mode = modes
    except TypeError:  # tt-metal 0.6x has 32 circular buffers
        config.unpack_to_dest_mode = modes[:32]
    base, rest = divmod(TILES, len(cores))
    counts = [base + (i < rest) for i in range(len(cores))]
    starts = [sum(counts[:i]) for i in range(len(cores))]
    addrs = [x.buffer_address() for x in tensors]
    reader_rt = {c: [n, s0, *addrs] for c, n, s0 in zip(cores, counts, starts)}
    writer_rt = {c: ([1, i] if reduce else [n, s0]) + [out.buffer_address()]
                 for i, (c, n, s0) in enumerate(zip(cores, counts, starts))}  # fmt: skip
    compute_rt = {c: [n] for c, n in zip(cores, counts)}
    src = source_code(ttnn)
    # a sharded array's kernel addresses its core's shard directly: no TensorAccessor, no compile-time args
    per_input = [a for name, x in zip(names, tensors) if placed[name]["kind"] == "interleaved"
                 for a in ttnn.TensorAccessorArgs(x).get_compile_time_args()]  # fmt: skip
    out_args = (
        [] if placed[task["output"]]["kind"] == "sharded" else ttnn.TensorAccessorArgs(out).get_compile_time_args()
    )
    kernels = [
        ttnn.KernelDescriptor(kernel_source=(folder / "reader.cpp").read_text(), source_type=src, core_ranges=core,
                              compile_time_args=per_input, runtime_args=per_core(ttnn, reader_rt),
                              config=ttnn.ReaderConfigDescriptor()),
        ttnn.KernelDescriptor(kernel_source=(folder / "writer.cpp").read_text(), source_type=src, core_ranges=core,
                              compile_time_args=out_args,
                              runtime_args=per_core(ttnn, writer_rt), config=ttnn.WriterConfigDescriptor()),
        ttnn.KernelDescriptor(kernel_source=(folder / "compute.cpp").read_text(), source_type=src, core_ranges=core,
                              compile_time_args=[], runtime_args=per_core(ttnn, compute_rt), config=config),
    ]  # fmt: skip
    program = ttnn.ProgramDescriptor(kernels=kernels, semaphores=[], cbs=cbs)
    got = ttnn.to_torch(ttnn.generic_op([*tensors, out], program))
    return {**verdict_of(task, got, want), "cores": len(cores)}


def main() -> int:
    import ttnn  # pyright: ignore[reportMissingImports]

    dev = ttnn.open_device(device_id=0)
    try:
        for name in sys.argv[1:]:
            folder = pathlib.Path(name)
            try:
                verdict = run(dev, folder)
            except Exception as err:
                text = str(err)  # a compile error leads the message, the build's stack ends it
                shown = text if len(text) < 4000 else f"{text[:3000]} ... {text[-800:]}"
                verdict = {"ok": False, "err": None, "abs": None, "error": f"{type(err).__name__}: {shown}"}
            print("TENSIXGEN-VERDICT " + json.dumps({"name": folder.name, **verdict}), flush=True)
    finally:
        ttnn.close_device(dev)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
