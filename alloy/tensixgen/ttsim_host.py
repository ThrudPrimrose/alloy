# Copyright 2026 ETH Zurich and the Alloy authors.
"""Runs generated Tensix programs (alloy.tensixgen) on a device ttnn opens (ttsim through TT_METAL_SIMULATOR, or a
card) under the eval contract v2 of alloy-tenstorrent ``agents/SPEC.md``, and prints one JSON verdict per program.
Standalone: it runs inside a tt-metal image and never imports alloy. Inputs, reference
and verdict are agents/host.py's ``task_run``: seeded float32 inputs over each input's range, the float64 program as
the reference, |got - ref| <= 1e-5 + 1e-3 |ref|, and a sum's partial tiles added in float64 with the allowance
2^-23 sqrt(N) |ref|. Its cores are the descriptor's (``options.cores``, 0 the whole grid).

    python3 ttsim_host.py FOLDER...   # each: reader.cpp, compute.cpp, writer.cpp, config.json, program.json
"""

import json
import math
import pathlib
import sys
import traceback

TILES = 1024
OUT_CB = 16
FP32_EPS = 2.0**-23
CALLS = ("exp", "log", "sqrt", "sin", "cos", "tanh", "abs")


def evaluate(program: list, arrays: dict, calls: dict):
    scope = dict(calls) | dict(arrays)
    target = ""
    for line in program:
        target, expression = line.split(" = ", 1)
        scope[target] = eval(expression, {"__builtins__": {}}, scope)
    return scope[target]


def operands(task: dict):
    """host.py's ``task_operands``: the same seed, draw and float64 reference."""
    import torch

    g = torch.Generator().manual_seed(1234)
    shape = (TILES * 32, 32)
    xs = [(torch.rand(shape, generator=g, dtype=torch.float64) * (hi - lo) + lo).float().double()
          for _, lo, hi in task["inputs"]]  # fmt: skip
    calls = {name: getattr(torch, name) for name in CALLS} | {"sum": torch.sum, "max": torch.max}
    return xs, evaluate(task["program"], {n: x for (n, *_), x in zip(task["inputs"], xs)}, calls)


def verdict_of(task: dict, got, want) -> dict:
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


def unpack_mode(ttnn):
    """``UnpackToDestMode``: tt-metal 0.6x binds it only in the program-descriptor module (tensix_harness.py)."""
    try:
        return ttnn.UnpackToDestMode
    except AttributeError:
        return ttnn._ttnn.program_descriptor.UnpackToDestMode


def source_code(ttnn):
    """The inline-source kernel type: nested in ``KernelDescriptor`` in 0.8x, a module enum in 0.6x."""
    try:
        return ttnn.KernelDescriptor.SourceType.SOURCE_CODE
    except AttributeError:
        return ttnn._ttnn.program_descriptor.SourceType.SOURCE_CODE


def per_core(ttnn, values: dict):
    """Runtime arguments per core (x, y): ``RuntimeArgs`` in tt-metal 0.8x, nested lists ``[x][y]`` in 0.6x."""
    gx, gy = max(x for x, _ in values) + 1, max(y for _, y in values) + 1
    try:
        args = ttnn.RuntimeArgs()
    except AttributeError:
        return [[values.get((x, y), []) for y in range(gy)] for x in range(gx)]
    for (x, y), v in values.items():
        args[x][y] = v
    return args


def run(dev, folder: pathlib.Path) -> dict:
    import ttnn  # pyright: ignore[reportMissingImports] -- only inside the tt-metal image

    task = json.loads((folder / "program.json").read_text())
    cfg = json.loads((folder / "config.json").read_text())
    xs, want = operands(task)
    mem = ttnn.DRAM_MEMORY_CONFIG
    tensors = [ttnn.from_torch(x.float(), dtype=ttnn.float32, layout=ttnn.TILE_LAYOUT, device=dev, memory_config=mem)
               for x in xs]  # fmt: skip
    grid = dev.compute_with_storage_grid_size()
    cores = [(x, y) for y in range(grid.y) for x in range(grid.x)]  # core index = y * grid.x + x
    cores = cores[: task["options"]["cores"] or len(cores)]
    assert len(cores) <= TILES, f"{len(cores)} cores for {TILES} tiles: a core without a tile hangs"
    core = ttnn.CoreRangeSet([ttnn.CoreRange(ttnn.CoreCoord(x, y), ttnn.CoreCoord(x, y)) for x, y in cores])
    reduce = bool(task["reduce"])
    out_shape = [32 * len(cores), 32] if reduce else list(xs[0].shape)
    out = ttnn.allocate_tensor_on_device(ttnn.Shape(out_shape), ttnn.float32, ttnn.TILE_LAYOUT, dev, mem)
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
    per_input = [a for x in tensors for a in ttnn.TensorAccessorArgs(x).get_compile_time_args()]
    kernels = [
        ttnn.KernelDescriptor(kernel_source=(folder / "reader.cpp").read_text(), source_type=src, core_ranges=core,
                              compile_time_args=per_input, runtime_args=per_core(ttnn, reader_rt),
                              config=ttnn.ReaderConfigDescriptor()),
        ttnn.KernelDescriptor(kernel_source=(folder / "writer.cpp").read_text(), source_type=src, core_ranges=core,
                              compile_time_args=ttnn.TensorAccessorArgs(out).get_compile_time_args(),
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
