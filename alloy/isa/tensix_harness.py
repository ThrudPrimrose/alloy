# Copyright 2026 ETH Zurich and the Alloy authors.
"""Runs Tensix table rows on a device ttnn opens (a Blackhole, or ttsim through TT_METAL_SIMULATOR) and prints one JSON
verdict per row. Standalone: it runs inside a tt-metal image (Python 3.10, ttnn, torch) and never imports alloy; the
kernel sources below need neither ttnn nor torch, so alloy's tests read them.

    python3 tensix_harness.py rows.json   # rows: [{"op", "dtype", "kind", "unit", "header", "init", "call", ...}]

Each row runs through a one-core program of inline kernels: a reader, a compute kernel whose body is the row's
``init`` and ``call``, and a writer, so a verdict says the row's spelling compiled for the device and computed the op.
The scaffolding follows the tt-metal version (``new``): 0.8x moved the kernel headers under ``api/``, renamed the
compute entry ``kernel_main`` and the start-up calls."""

import json
import math
import os
import pathlib
import sys
import traceback

TILE = 1024
TILES = 2
#: Output circular buffer; inputs take CBs 0 and 1.
OUT_CB = 16


def compute_include(header: str, new: bool) -> str:
    """``header`` of the compute API; 0.6x keeps ``compute_kernel_api.h`` itself at the include root."""
    if new:
        return f"api/compute/{header}"
    return header if header == "compute_kernel_api.h" else f"compute_kernel_api/{header}"


def dataflow_include(new: bool) -> str:
    return "api/dataflow/dataflow_api.h" if new else "dataflow_api.h"


def reader(offsets: list[int], new: bool) -> str:
    """A reader of ``len(offsets)`` inputs, input ``k`` into CB ``k``; its accessor's compile-time args start at
    ``offsets[k]`` (the host knows each accessor's count)."""
    accessors = "".join(
        f"""
    constexpr auto args{cb} = TensorAccessorArgs<{offset}>();
    const auto s{cb} = TensorAccessor(args{cb}, get_arg_val<uint32_t>({cb + 1}), get_tile_size({cb}));"""
        for cb, offset in enumerate(offsets)
    )
    reads = "".join(
        f"""
        cb_reserve_back({cb}, 1);
        noc_async_read_tile(i, s{cb}, get_write_ptr({cb}));
        noc_async_read_barrier();
        cb_push_back({cb}, 1);"""
        for cb in range(len(offsets))
    )
    return f"""
#include <stdint.h>
#include "{dataflow_include(new)}"
void kernel_main() {{
    uint32_t num_tiles = get_arg_val<uint32_t>(0);{accessors}
    for (uint32_t i = 0; i < num_tiles; ++i) {{{reads}
    }}
}}
"""


def writer(new: bool) -> str:
    return f"""
#include <stdint.h>
#include "{dataflow_include(new)}"
void kernel_main() {{
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr uint32_t cb = {OUT_CB};
    constexpr auto args = TensorAccessorArgs<0>();
    const auto s = TensorAccessor(args, get_arg_val<uint32_t>(1), get_tile_size(cb));
    for (uint32_t i = 0; i < num_tiles; ++i) {{
        cb_wait_front(cb, 1);
        noc_async_write_tile(i, s, get_read_ptr(cb));
        noc_async_write_barrier();
        cb_pop_front(cb, 1);
    }}
}}
"""


def spelled(value: "str | dict", new: bool) -> str:
    """A row's ``init`` or ``call``: one spelling, or the one of this tt-metal version (``v06``, ``v08``)."""
    return value if isinstance(value, str) else value["v08" if new else "v06"]


def body(row: dict, new: bool) -> "tuple[str, str, str]":
    """The start-up, the per-tile body and the pops of ``row``'s kind: a unary row copies its tile to DST for the
    SFPU; a binary SFPU row copies both operands to DST; a binary FPU row reads both from their CBs."""
    init, call = spelled(row["init"], new), spelled(row["call"], new)
    if row["kind"] == "unary":
        start = "compute_kernel_hw_startup(c0, c16);\n    copy_init(c0);" if new else "init_sfpu(c0, c16);"
        steps = f"cb_wait_front(c0, 1);\n        copy_tile(c0, 0, 0);\n        {init};\n        {call};"
        return start, steps, "cb_pop_front(c0, 1);"
    pops = "cb_pop_front(c0, 1);\n        cb_pop_front(c1, 1);"
    if row["kind"] == "binary_sfpu":
        start = "compute_kernel_hw_startup(c0, c16);" if new else "init_sfpu(c0, c16);"
        copy = "copy_init" if new else "copy_tile_to_dst_init_short"
        steps = (
            f"cb_wait_front(c0, 1);\n        cb_wait_front(c1, 1);\n        {copy}(c0);\n        copy_tile(c0, 0, 0);"
            f"\n        {copy}(c1);\n        copy_tile(c1, 0, 1);\n        {init};\n        {call};"
        )
        return start, steps, pops
    start = "compute_kernel_hw_startup(c0, c1, c16);" if new else "binary_op_init_common(c0, c1, c16);"
    steps = f"cb_wait_front(c0, 1);\n        cb_wait_front(c1, 1);\n        {init};\n        {call};"
    return start, steps, pops


def compute(row: dict, new: bool) -> str:
    """The compute kernel of ``row`` for tt-metal 0.8x (``new``) or 0.6x."""
    headers = ("common.h", "tile_move_copy.h", "eltwise_unary/eltwise_unary.h", "eltwise_binary.h", row["header"])
    includes = "\n".join(f'#include "{compute_include(h, new)}"' for h in dict.fromkeys(headers))
    entry = "void kernel_main()" if new else "namespace NAMESPACE {\nvoid MAIN"
    close = "" if new else "}  // namespace NAMESPACE"
    start, steps, pops = body(row, new)
    return f"""
#include <cstdint>
{includes}
{entry} {{
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr auto c0 = tt::CBIndex::c_0;
    constexpr auto c1 = tt::CBIndex::c_1;
    constexpr auto c16 = tt::CBIndex::c_{OUT_CB};
    {start}
    for (uint32_t i = 0; i < num_tiles; ++i) {{
        cb_reserve_back(c16, 1);
        tile_regs_acquire();
        {steps}
        tile_regs_commit();
        tile_regs_wait();
        pack_tile(0, c16);
        {pops}
        tile_regs_release();
        cb_push_back(c16, 1);
    }}
}}
{close}
"""


def new_api() -> bool:
    """Whether this tt-metal keeps its kernel API under ``hw/inc/api/`` (0.8x), in the ttnn wheel or ``$TT_METAL_HOME``."""
    import ttnn  # pyright: ignore[reportMissingImports] -- only inside the tt-metal image

    roots = [pathlib.Path(str(ttnn.__file__)).parent / "tt_metal"]
    home = os.environ.get("TT_METAL_HOME")
    if home:
        roots.append(pathlib.Path(home) / "tt_metal")
    return any((root / "hw/inc/api/compute").is_dir() for root in roots)


def inputs(row: dict) -> list:
    """Operands drawn from the row's domain ``[lo, hi]``, every element distinct, shaped as TILES tiles."""
    import torch

    lo, hi = row["domain"]
    count = 1 if row["kind"] == "unary" else 2
    base = torch.linspace(lo, hi, TILES * TILE, dtype=torch.float32)
    return [base.roll(k * 97).reshape(TILES * 32, 32) for k in range(count)]


def reference(op: str, xs: list):
    import torch

    x = xs[0].double()
    unary = {
        "exp": torch.exp, "log": torch.log, "sqrt": torch.sqrt, "rsqrt": torch.rsqrt, "recip": torch.reciprocal,
        "abs": torch.abs, "neg": torch.neg, "tanh": torch.tanh, "sin": torch.sin, "cos": torch.cos,
    }  # fmt: skip
    if op in unary:
        return unary[op](x)
    y = xs[1].double()
    return {"add": x + y, "sub": x - y, "mul": x * y, "div": x / y}[op]


def run(dev, row: dict, new: bool) -> dict:
    import torch
    import ttnn  # pyright: ignore[reportMissingImports] -- only inside the tt-metal image

    tt_dtype, torch_dtype, page = {
        "f32": (ttnn.float32, torch.float32, 4096),
        "bf16": (ttnn.bfloat16, torch.bfloat16, 2048),
    }[row["dtype"]]
    xs = [x.to(torch_dtype) for x in inputs(row)]
    core = ttnn.CoreRangeSet([ttnn.CoreRange(ttnn.CoreCoord(0, 0), ttnn.CoreCoord(0, 0))])
    memory = ttnn.DRAM_MEMORY_CONFIG
    tensors = [
        ttnn.from_torch(x, dtype=tt_dtype, layout=ttnn.TILE_LAYOUT, device=dev, memory_config=memory) for x in xs
    ]
    out = ttnn.allocate_tensor_on_device(ttnn.Shape(list(xs[0].shape)), tt_dtype, ttnn.TILE_LAYOUT, dev, memory)
    cbs = [
        ttnn.CBDescriptor(
            total_size=2 * page,
            core_ranges=core,
            format_descriptors=[ttnn.CBFormatDescriptor(buffer_index=i, data_format=tt_dtype, page_size=page)],
        )
        for i in [*range(len(xs)), OUT_CB]
    ]
    reader_args, writer_args, compute_args = ttnn.RuntimeArgs(), ttnn.RuntimeArgs(), ttnn.RuntimeArgs()
    reader_args[0][0] = [TILES, *(t.buffer_address() for t in tensors)]
    writer_args[0][0] = [TILES, out.buffer_address()]
    compute_args[0][0] = [TILES]
    per_input = [list(ttnn.TensorAccessorArgs(t).get_compile_time_args()) for t in tensors]
    offsets = [sum(len(a) for a in per_input[:k]) for k in range(len(per_input))]
    config = ttnn.ComputeConfigDescriptor()
    config.fp32_dest_acc_en = row["dtype"] == "f32"
    config.math_approx_mode = False
    config.math_fidelity = ttnn.MathFidelity.HiFi4  # LoFi, the default, multiplies with truncated mantissas
    if (
        row["dtype"] == "f32" and row["kind"] != "binary"
    ):  # FPU operands unpack to SrcA/SrcB (TF32): only DST takes FP32
        config.unpack_to_dest_mode = [ttnn.UnpackToDestMode.UnpackToDestFp32] * 64
    source = ttnn.KernelDescriptor.SourceType.SOURCE_CODE
    kernels = [
        ttnn.KernelDescriptor(
            kernel_source=reader(offsets, new), source_type=source, core_ranges=core,
            compile_time_args=[a for args in per_input for a in args], runtime_args=reader_args,
            config=ttnn.ReaderConfigDescriptor(),
        ),
        ttnn.KernelDescriptor(
            kernel_source=writer(new), source_type=source, core_ranges=core,
            compile_time_args=ttnn.TensorAccessorArgs(out).get_compile_time_args(), runtime_args=writer_args,
            config=ttnn.WriterConfigDescriptor(),
        ),
        ttnn.KernelDescriptor(
            kernel_source=compute(row, new), source_type=source, core_ranges=core, compile_time_args=[],
            runtime_args=compute_args, config=config,
        ),
    ]  # fmt: skip
    program = ttnn.ProgramDescriptor(kernels=kernels, semaphores=[], cbs=cbs)
    got = ttnn.to_torch(ttnn.generic_op([*tensors, out], program))
    want = reference(row["op"], [x.float() for x in xs])
    rel = ((got.double() - want).abs() / want.abs().clamp_min(1e-30)).max().item()
    return {"ok": bool(math.isfinite(rel) and rel <= row["tol"]), "rel": rel}


def main() -> int:
    import ttnn  # pyright: ignore[reportMissingImports] -- only inside the tt-metal image

    with open(sys.argv[1]) as handle:
        rows = json.load(handle)
    new = new_api()
    dev = ttnn.open_device(device_id=0)
    try:
        for row in rows:
            key = {k: row[k] for k in ("op", "dtype", "unit")}
            try:
                verdict = run(dev, row, new)
            except Exception as err:
                verdict = {"ok": False, "rel": None, "error": f"{type(err).__name__}: {str(err)[-600:]}"}
            print("TENSIX-VERDICT " + json.dumps({**key, **verdict}), flush=True)
    finally:
        ttnn.close_device(dev)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(2)
