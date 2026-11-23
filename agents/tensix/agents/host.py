"""Runs agent-written Tensix kernels (agents/submissions/<name>/{reader,compute,writer}.cpp, config.json) under the
fixed host contract of agents/SPEC.md on one core of the card, and prints one AGENT-VERDICT line per submission."""

import json
import math
import pathlib
import sys
import time
import traceback

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE.parent / "rows"))
from tensix_harness import runtime_args, source_code, unpack_mode

ELEM_TILES, MM_TILES = 1024, 16  # 1,048,576 f32 elements; 512 x 512 matmul
OUT_CB = 16


#: The eval tasks (alloy/hb_plugin/eval_set.py): name -> kind, inputs [(name, low, high)], output, program.
TASKS = {t["name"]: t for t in json.loads((HERE / "tasks.json").read_text())} if (HERE / "tasks.json").exists() else {}
#: What a task program's calls mean in the float64 reference and in ttnn's stock ops.
TORCH_CALLS = ("exp", "log", "sqrt", "sin", "cos", "tanh", "abs")


def evaluate(task: dict, arrays: dict, calls: dict):
    """The task's program over ``arrays`` with ``calls`` for its functions; the output's value."""
    scope = dict(calls) | dict(arrays)
    for line in task["program"]:
        target, expression = line.split(" = ", 1)
        scope[target] = eval(expression, {"__builtins__": {}}, scope)
    return scope[task["output"]]


def task_operands(task: dict):
    """Seeded inputs over each input's domain, as the card holds them (f32), and the float64 reference of the
    program on those f32 values (a reduction's is one value)."""
    import torch

    g = torch.Generator().manual_seed(1234)
    shape = (ELEM_TILES * 32, 32)
    xs = [(torch.rand(shape, generator=g, dtype=torch.float64) * (hi - lo) + lo).float().double()
          for _, lo, hi in task["inputs"]]  # fmt: skip
    calls = {name: getattr(torch, name) for name in TORCH_CALLS} | {"sum": torch.sum, "max": torch.max}
    return xs, evaluate(task, {n: x for (n, *_), x in zip(task["inputs"], xs)}, calls)


def kernel_of(name: str) -> str:
    for k in sorted(TASKS, key=len, reverse=True):
        if name.startswith(k):
            return k
    for k in (
        "fuse_diamond",
        "tsvc_2_s451",
        "transc_log_wide",
        "matmul",
        "probe_exp_wide",
        "probe_exp",
        "probe_log",
        "probe_div",
        "probe_sqrt",
    ):
        if name.startswith(k):
            return k
    raise ValueError(name)


def operands(kernel: str):
    import torch

    g = torch.Generator().manual_seed(1234)
    shape = (ELEM_TILES * 32, 32)
    if kernel == "fuse_diamond":
        a = torch.rand(shape, generator=g, dtype=torch.float64) * 4 - 2
        return [a], (a * a + 1) * (a * a - 1)
    if kernel == "tsvc_2_s451":
        b = (torch.rand(shape, generator=g, dtype=torch.float64) * 2 - 1) * math.pi
        c = (torch.rand(shape, generator=g, dtype=torch.float64) * 2 - 1) * math.pi
        return [b, c], torch.sin(b) + torch.cos(c)
    if kernel == "probe_exp_wide":  # exp past both ends of f32's range: overflow to inf, underflow to 0
        x = torch.rand(shape, generator=g, dtype=torch.float64) * 200 - 100
        return [x], torch.exp(x)
    if kernel == "probe_exp":  # exp alone, over the range a log's exp(y) step sees
        x = torch.rand(shape, generator=g, dtype=torch.float64) * 14 - 7
        return [x], torch.exp(x)
    if kernel == "probe_div":  # division alone, both operands over six decades
        a = 10.0 ** (torch.rand(shape, generator=g, dtype=torch.float64) * 6 - 3)
        b = 10.0 ** (torch.rand(shape, generator=g, dtype=torch.float64) * 6 - 3)
        return [a, b], a / b
    if kernel == "probe_sqrt":  # sqrt alone, over six decades
        x = 10.0 ** (torch.rand(shape, generator=g, dtype=torch.float64) * 6 - 3)
        return [x], torch.sqrt(x)
    if kernel in ("transc_log_wide", "probe_log"):
        x = 10.0 ** (torch.rand(shape, generator=g, dtype=torch.float64) * 6 - 3)
        return [x], torch.log(x)
    n = MM_TILES * 32
    a = (torch.rand((n, n), generator=g) * 2 - 1).to(torch.bfloat16)
    b = (torch.rand((n, n), generator=g) * 2 - 1).to(torch.bfloat16)
    return [a, b], a.double() @ b.double()


def bins(x0, diff, want) -> list[list[float]]:
    """Six bins of the first input by value: [low, high, max abs error, max rel error] each, 3 significant digits."""
    import torch

    order = torch.argsort(x0)
    rows = []
    for part in torch.tensor_split(order, 6):
        d, w = diff[part], want[part].abs().clamp_min(1e-30)
        rows.append(
            [
                float(f"{v:.3g}")
                for v in (x0[part].min().item(), x0[part].max().item(), d.max().item(), (d / w).max().item())
            ]
        )
    return rows


def judge_digest() -> str:
    """sha256 (12 hex) of what decides a verdict: this host, the job runner and the spec (fairness audit F16)."""
    import hashlib

    h = hashlib.sha256()
    for name in ("host.py", "job.py", "SPEC.md"):
        h.update((HERE / name).read_bytes())
    return h.hexdigest()[:12]


def stamps(folder: pathlib.Path) -> dict:
    """The judge's digest and the submission's run record (RUN.json: arm, model, tool commit, brief digest; F14)."""
    record = folder / "RUN.json"
    return {"judge": judge_digest(), "run": json.loads(record.read_text()) if record.exists() else None}


def grid_args(ttnn, values):
    """Runtime arguments: a list is core (0, 0)'s; a dict maps (x, y) to each core's list (0.6x: nested lists [x][y]
    over the grid, 0.8x: ``RuntimeArgs``)."""
    if isinstance(values, list):
        return runtime_args(ttnn, values)
    gx, gy = max(x for x, _ in values) + 1, max(y for _, y in values) + 1
    try:
        args = ttnn.RuntimeArgs()
    except AttributeError:
        return [[values.get((x, y), []) for y in range(gy)] for x in range(gx)]
    for (x, y), v in values.items():
        args[x][y] = v
    return args


def descriptor(ttnn, folder, cfg, core, cb_plan, tensors, out, reader_rt, writer_rt, compute_rt, sharded=frozenset()):
    """The program of the folder's three kernels on ``core`` (a range set): its circular buffers, compute config and
    arguments (one list for core (0, 0), or a dict per core). ``sharded`` holds the indices of L1-sharded inputs (and
    -1 for the output): their kernels address the core's shard directly, with no TensorAccessor arguments."""
    fmt = {"float32": (ttnn.float32, 4096), "bfloat16": (ttnn.bfloat16, 2048)}
    cbs = [
        ttnn.CBDescriptor(total_size=tiles * fmt[f][1], core_ranges=core,
                          format_descriptors=[ttnn.CBFormatDescriptor(buffer_index=i, data_format=fmt[f][0], page_size=fmt[f][1])])
        for i, (tiles, f) in sorted(cb_plan.items())
    ]  # fmt: skip
    config = ttnn.ComputeConfigDescriptor()
    config.fp32_dest_acc_en = bool(cfg.get("fp32_dest_acc_en", True))
    config.math_approx_mode = bool(cfg.get("math_approx_mode", False))
    config.math_fidelity = getattr(ttnn.MathFidelity, cfg.get("math_fidelity", "HiFi4"))
    modes = [unpack_mode(ttnn).Default] * 32
    for i in cfg.get("unpack_to_dest_fp32", []):
        modes[int(i)] = unpack_mode(ttnn).UnpackToDestFp32
    config.unpack_to_dest_mode = modes
    src = source_code(ttnn)
    per_input = [
        a for k, x in enumerate(tensors) if k not in sharded for a in ttnn.TensorAccessorArgs(x).get_compile_time_args()
    ]
    out_args = [] if -1 in sharded else ttnn.TensorAccessorArgs(out).get_compile_time_args()
    kernels = [
        ttnn.KernelDescriptor(kernel_source=(folder / "reader.cpp").read_text(), source_type=src, core_ranges=core,
                              compile_time_args=per_input, runtime_args=grid_args(ttnn, reader_rt), config=ttnn.ReaderConfigDescriptor()),
        ttnn.KernelDescriptor(kernel_source=(folder / "writer.cpp").read_text(), source_type=src, core_ranges=core,
                              compile_time_args=out_args,
                              runtime_args=grid_args(ttnn, writer_rt), config=ttnn.WriterConfigDescriptor()),
        ttnn.KernelDescriptor(kernel_source=(folder / "compute.cpp").read_text(), source_type=src, core_ranges=core,
                              compile_time_args=[], runtime_args=grid_args(ttnn, compute_rt), config=config),
    ]  # fmt: skip
    return ttnn.ProgramDescriptor(kernels=kernels, semaphores=[], cbs=cbs)


def run(dev, folder: pathlib.Path) -> dict:
    import torch
    import ttnn  # pyright: ignore[reportMissingImports] -- only inside the tt-metal image

    kernel = kernel_of(folder.name)
    if kernel in TASKS:
        return task_run(dev, folder, TASKS[kernel])
    cfg = json.loads((folder / "config.json").read_text())
    xs, want = operands(kernel)
    core = ttnn.CoreRangeSet([ttnn.CoreRange(ttnn.CoreCoord(0, 0), ttnn.CoreCoord(0, 0))])
    mem = ttnn.DRAM_MEMORY_CONFIG
    fmt = {"float32": (ttnn.float32, 4096), "bfloat16": (ttnn.bfloat16, 2048)}
    if kernel == "matmul":
        tensors = [
            ttnn.from_torch(x, dtype=ttnn.bfloat16, layout=ttnn.TILE_LAYOUT, device=dev, memory_config=mem) for x in xs
        ]
        out = ttnn.allocate_tensor_on_device(ttnn.Shape([MM_TILES * 32] * 2), ttnn.float32, ttnn.TILE_LAYOUT, dev, mem)
        cb_plan = {0: (2, "bfloat16"), 1: (2, "bfloat16"), OUT_CB: (2, "float32")}
        t = MM_TILES
        reader_rt, writer_rt, compute_rt = (
            [t, t, t, *(x.buffer_address() for x in tensors)],
            [t * t, out.buffer_address()],
            [t, t, t],
        )
    else:
        tensors = [
            ttnn.from_torch(x.float(), dtype=ttnn.float32, layout=ttnn.TILE_LAYOUT, device=dev, memory_config=mem)
            for x in xs
        ]
        out = ttnn.allocate_tensor_on_device(ttnn.Shape(list(xs[0].shape)), ttnn.float32, ttnn.TILE_LAYOUT, dev, mem)
        cb_plan = dict.fromkeys(range(len(xs)), (2, "float32")) | {OUT_CB: (2, "float32")}
        reader_rt, writer_rt, compute_rt = (
            [ELEM_TILES, *(x.buffer_address() for x in tensors)],
            [ELEM_TILES, out.buffer_address()],
            [ELEM_TILES],
        )
    for extra in cfg.get("extra_cbs", []):
        cb_plan[int(extra["index"])] = (int(extra["tiles"]), extra["format"])
    program = descriptor(ttnn, folder, cfg, core, cb_plan, tensors, out, reader_rt, writer_rt, compute_rt)
    got = ttnn.to_torch(ttnn.generic_op([*tensors, out], program)).double()
    if kernel == "matmul":
        err = ((got - want).norm() / want.norm()).item()
        ok = math.isfinite(err) and err <= 1e-2
    else:
        x0 = xs[0].float().double().flatten()  # the input as the card saw it (f32)
        want = want.flatten() if kernel not in ("transc_log_wide", "probe_log") else torch.log(x0)
        want = torch.exp(x0) if kernel == "probe_exp" else want
        if kernel == "probe_exp_wide":  # the f32 result: inf past FLT_MAX, flushed to 0 below the smallest normal
            want = torch.exp(x0).float().double()
            want = torch.where(want.abs() < 1.1754943508222875e-38, torch.zeros_like(want), want)
        want = torch.sqrt(x0) if kernel == "probe_sqrt" else want
        got = got.flatten()
        diff = torch.where(torch.isinf(want) & (got == want), torch.zeros_like(want), (got - want).abs())
        over = diff - (1e-5 + 1e-3 * want.abs())
        excess = over.max().item()
        err = (diff / want.abs().clamp_min(1e-30)).max().item()
        ok = math.isfinite(excess) and excess <= 0
        at = int(over.argmax())
        extra = {
            "abs": diff.max().item(),
            "worst": [x0[at].item(), got[at].item(), want[at].item()],
            "bins": bins(x0, diff, want),
        }
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        ttnn.generic_op([*tensors, out], program)
        ttnn.synchronize_device(dev)
        times.append(time.perf_counter() - t0)
    return {
        "ok": bool(ok),
        "err": err,
        "ms": sorted(times)[2] * 1e3,
        **(extra if kernel != "matmul" else {}),
        **stamps(folder),
    }


#: fp32's unit roundoff: a reduction of N terms may also drift by FP32_EPS * sqrt(N) of its value (the bench's
#: reassociation allowance, hpcagent_bench.precision.accumulation_growth).
FP32_EPS = 2.0**-23


def verdict_of(task: dict, got, want) -> dict:
    """``got`` against the reference: |got - want| <= 1e-5 + 1e-3 |want| everywhere; a reduction's result is the
    float64 sum of its output, one partial-sum tile per core, with the bench's reassociation allowance on top."""
    import torch

    got, want = got.double().flatten(), torch.as_tensor(want, dtype=torch.float64).flatten()
    rtol = 1e-3
    if task["kind"] == "reduce":
        got = got.sum().reshape(1)  # every core's partial-sum tile
        rtol += FP32_EPS * math.sqrt(ELEM_TILES * 32 * 32)
    diff = (got - want).abs()
    excess = (diff - (1e-5 + rtol * want.abs())).max().item()
    err = (diff / want.abs().clamp_min(1e-30)).max().item()
    return {"ok": bool(math.isfinite(excess) and excess <= 0), "err": err, "abs": diff.max().item()}


def timed(call, dev) -> float:
    """Median of five runs in ms."""
    import ttnn  # pyright: ignore[reportMissingImports]

    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        call()
        ttnn.synchronize_device(dev)
        times.append(time.perf_counter() - t0)
    return sorted(times)[2] * 1e3


def task_run(dev, folder: pathlib.Path, task: dict) -> dict:
    """An eval task: the agent's kernels under the contract of SPEC.md, or (a folder under stock/) the program in
    ttnn's stock ops, the baseline and the reference solution every eval task must have before the freeze."""
    import ttnn  # pyright: ignore[reportMissingImports]

    xs, want = task_operands(task)
    mem = ttnn.DRAM_MEMORY_CONFIG
    if folder.parent.name == "stock":
        tensors = [
            ttnn.from_torch(x.float(), dtype=ttnn.float32, layout=ttnn.TILE_LAYOUT, device=dev, memory_config=mem)
            for x in xs
        ]
        calls = {name: getattr(ttnn, name) for name in TORCH_CALLS} | {"sum": ttnn.sum, "max": ttnn.max}
        arrays = {n: t for (n, *_), t in zip(task["inputs"], tensors)}
        got = ttnn.to_torch(evaluate(task, arrays, calls))
        return {**verdict_of(task, got, want), "ms": timed(lambda: evaluate(task, arrays, calls), dev), "stock": True}
    cfg = json.loads((folder / "config.json").read_text())
    grid = dev.compute_with_storage_grid_size()
    cores = [(x, y) for y in range(grid.y) for x in range(grid.x)]  # core index = y * grid.x + x
    described = folder / "program.json"  # a generated program's cores (options.cores, 0 the whole grid) and placement
    program_json = json.loads(described.read_text()) if described.exists() else {}
    count = program_json["options"]["cores"] if program_json else 0
    cores = cores[: count or len(cores)]
    assert len(cores) <= ELEM_TILES, f"{len(cores)} cores for {ELEM_TILES} tiles: a core without a tile hangs"
    core = ttnn.CoreRangeSet([ttnn.CoreRange(ttnn.CoreCoord(x, y), ttnn.CoreCoord(x, y)) for x, y in cores])
    placed = program_json.get("placement", {})

    def memory(name):
        """DRAM interleaved, or L1 height sharded as program.json says: ``tiles`` tile rows on each core, shard k on
        core k."""
        if placed.get(name, {}).get("kind", "interleaved") == "interleaved":
            return mem
        assert placed[name]["cores"] == len(cores), f"{name} is sharded over {placed[name]['cores']} cores"
        spec = ttnn.ShardSpec(core, [32 * placed[name]["tiles"], 32], ttnn.ShardOrientation.ROW_MAJOR)
        return ttnn.MemoryConfig(ttnn.TensorMemoryLayout.HEIGHT_SHARDED, ttnn.BufferType.L1, spec)

    names = [name for name, *_ in task["inputs"]]
    tensors = [ttnn.from_torch(x.float(), dtype=ttnn.float32, layout=ttnn.TILE_LAYOUT, device=dev,
                               memory_config=memory(name)) for name, x in zip(names, xs)]  # fmt: skip
    sharded = {k for k, name in enumerate(names) if memory(name) is not mem}
    if memory(task["output"]) is not mem:
        sharded.add(-1)
    reduce = task["kind"] == "reduce"
    out_shape = [32 * len(cores), 32] if reduce else list(xs[0].shape)  # a reduction: one partial-sum tile per core
    out = ttnn.allocate_tensor_on_device(
        ttnn.Shape(out_shape), ttnn.float32, ttnn.TILE_LAYOUT, dev, memory(task["output"])
    )
    cb_plan = dict.fromkeys(range(len(xs)), (2, "float32")) | {OUT_CB: (2, "float32")}
    for extra in cfg.get("extra_cbs", []):
        cb_plan[int(extra["index"])] = (int(extra["tiles"]), extra["format"])
    base, rest = divmod(ELEM_TILES, len(cores))
    counts = [base + (i < rest) for i in range(len(cores))]
    starts = [sum(counts[:i]) for i in range(len(cores))]
    addrs = [x.buffer_address() for x in tensors]
    reader_rt = {c: [n, s0, *addrs] for c, n, s0 in zip(cores, counts, starts)}
    writer_rt = {c: ([1, i] if reduce else [n, s0]) + [out.buffer_address()]
                 for i, (c, n, s0) in enumerate(zip(cores, counts, starts))}  # fmt: skip
    compute_rt = {c: [n] for c, n in zip(cores, counts)}
    program = descriptor(
        ttnn, folder, cfg, core, cb_plan, tensors, out, reader_rt, writer_rt, compute_rt, frozenset(sharded)
    )
    got = ttnn.to_torch(ttnn.generic_op([*tensors, out], program))
    return {**verdict_of(task, got, want), "ms": timed(lambda: ttnn.generic_op([*tensors, out], program), dev),
            **stamps(folder)}  # fmt: skip


def main() -> int:
    import ttnn  # pyright: ignore[reportMissingImports]

    dev = ttnn.open_device(device_id=0)
    try:
        names = sys.argv[1:]
        found = (
            p
            for d in ("submissions", "probes", "stock", "reference", "generated")
            if (HERE / d).is_dir()
            for p in (HERE / d).iterdir()
        )
        for folder in sorted(found):
            if not folder.is_dir() or (names and not {folder.name, f"{folder.parent.name}/{folder.name}"} & set(names)):
                continue
            try:
                verdict = run(dev, folder)
            except Exception as err:
                verdict = {
                    "ok": False,
                    "err": None,
                    "ms": None,
                    "error": f"{type(err).__name__}: {str(err)[-1500:]}",
                    **stamps(folder),
                }
            shown = (
                f"{folder.parent.name}/{folder.name}"
                if folder.parent.name in ("stock", "reference", "generated")
                else folder.name
            )
            print("AGENT-VERDICT " + json.dumps({"name": shown, **verdict}), flush=True)
    finally:
        ttnn.close_device(dev)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
