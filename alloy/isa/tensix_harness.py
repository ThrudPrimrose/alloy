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
import re
import sys
import traceback
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    import torch
    import ttnn  # pyright: ignore[reportMissingImports] -- only inside the tt-metal image

TILE = 1024
TILES = 2
#: Output circular buffer; inputs take CBs 0 and 1.
OUT_CB = 16

#: A JSON object as the row files and verdicts hold it.
Json = dict[str, Any]


def compute_include(header: str, new: bool) -> str:
    """``header`` of the compute API; 0.6x keeps ``compute_kernel_api.h`` itself at the include root."""
    if new:
        return f"api/compute/{header}"
    return header if header == "compute_kernel_api.h" else f"compute_kernel_api/{header}"


def compute_headers(row: Json, new: bool) -> list[str]:
    """Every header the compute kernel of ``row`` includes, as include paths of tt-metal 0.8x (``new``) or 0.6x: the
    harness programs include exactly these, and the lookup prints them."""
    if row["kind"] == "matmul":
        names = ["common.h", "tile_move_copy.h", row["header"]]
        names += ["compute_kernel_hw_startup.h", "src_order.h"] if new else []
    elif row["kind"] == "reduction":
        names = ["common.h", row["header"]]
    else:
        names = ["common.h", "tile_move_copy.h", "eltwise_unary/eltwise_unary.h", "eltwise_binary.h", row["header"]]
    return [compute_include(h, new) for h in dict.fromkeys(names)]


def dataflow_include(new: bool) -> str:
    return "api/dataflow/dataflow_api.h" if new else "dataflow_api.h"


def reader(offsets: list[int], new: bool, once: int = -1) -> str:
    """A reader of ``len(offsets)`` inputs, input ``k`` into CB ``k``; its accessor's compile-time args start at
    ``offsets[k]`` (the host knows each accessor's count). Input ``once`` (a reduction's scaler) is one tile, read
    with the first tile of the others."""
    accessors = "".join(
        f"""
    constexpr auto args{cb} = TensorAccessorArgs<{offset}>();
    const auto s{cb} = TensorAccessor(args{cb}, get_arg_val<uint32_t>({cb + 1}), get_tile_size({cb}));"""
        for cb, offset in enumerate(offsets)
    )
    reads = "".join(
        f"""
        {"if (i == 0) " if cb == once else ""}{{
        cb_reserve_back({cb}, 1);
        noc_async_read_tile(i, s{cb}, get_write_ptr({cb}));
        noc_async_read_barrier();
        cb_push_back({cb}, 1);
        }}"""
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


def spelled(value: "str | Json", new: bool) -> str:
    """A row's ``init`` or ``call``: one spelling, or the one of this tt-metal version (``v06``, ``v08``)."""
    return value if isinstance(value, str) else value["v08" if new else "v06"]


def body(row: Json, new: bool) -> "tuple[str, str, str]":
    """The start-up, the per-tile body and the pops of ``row``'s kind: a unary row copies its tile to DST for the
    SFPU; a binary SFPU row copies both operands to DST; a binary FPU row reads both from their CBs."""
    init, call = spelled(row["init"], new), spelled(row["call"], new)
    if row["kind"] == "fill":  # no operand: the input tile is read and dropped, DST tile 0 is written
        start = "compute_kernel_hw_startup(c0, c16);" if new else "init_sfpu(c0, c16);"
        return start, f"cb_wait_front(c0, 1);\n        {init};\n        {call};", "cb_pop_front(c0, 1);"
    if row["kind"] in ("unary", "scan"):
        start = "compute_kernel_hw_startup(c0, c16);\n    copy_init(c0);" if new else "init_sfpu(c0, c16);"
        if row["kind"] == "scan":  # one init: the running totals stay in SFPU registers from tile to tile
            return (
                f"{start}\n    {init};",
                f"cb_wait_front(c0, 1);\n        copy_tile(c0, 0, 0);\n        {call};",
                "cb_pop_front(c0, 1);",
            )
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


def matmul_compute(row: Json, new: bool) -> str:
    """The compute kernel of a ``matmul`` row: one output tile accumulated in DST over ``num_tiles`` K tiles (tile
    ``kt`` of A from CB 0 and of B from CB 1), as tt-metal's single-core matmul example does. 0.8x starts the hardware
    with ``SrcOrder::Reverse`` (matmul sends in0 to SrcB) and inits with ``matmul_init``; 0.6x's ``mm_init`` does
    both."""
    includes = "\n".join(f'#include "{h}"' for h in compute_headers(row, new))
    entry = "void kernel_main()" if new else "namespace NAMESPACE {\nvoid MAIN"
    close = "" if new else "}  // namespace NAMESPACE"
    return f"""
#include <cstdint>
{includes}
{entry} {{
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr auto c0 = tt::CBIndex::c_0;
    constexpr auto c1 = tt::CBIndex::c_1;
    constexpr auto c16 = tt::CBIndex::c_{OUT_CB};
    {spelled(row["init"], new)};
    cb_reserve_back(c16, 1);
    tile_regs_acquire();
    for (uint32_t kt = 0; kt < num_tiles; ++kt) {{
        cb_wait_front(c0, 1);
        cb_wait_front(c1, 1);
        {spelled(row["call"], new)};
        cb_pop_front(c0, 1);
        cb_pop_front(c1, 1);
    }}
    tile_regs_commit();
    tile_regs_wait();
    pack_tile(0, c16);
    tile_regs_release();
    cb_push_back(c16, 1);
}}
{close}
"""


def reduction_compute(row: Json, new: bool) -> str:
    """The compute kernel of a ``reduction`` row: every data tile (CB 0) reduced into one DST tile against the scaler
    tile (CB 1), packed once, as tt-metal's ``reduce_w.cpp`` test kernel does. 0.6x's templates default to the
    ``REDUCE_OP`` and ``REDUCE_DIM`` macros, which its host defines; the kernel defines them from the row's init."""
    init = spelled(row["init"], new)
    found = re.search(r"<\s*([\w:]+)\s*,\s*([\w:]+)\s*>", init)
    if found is None:
        raise ValueError(f"a reduction's init names its PoolType and ReduceDim: {init}")
    pool, dim = found.groups()
    entry = "void kernel_main()" if new else "namespace NAMESPACE {\nvoid MAIN"
    close = "" if new else "}  // namespace NAMESPACE"
    return f"""
#include <cstdint>
#define REDUCE_OP {pool}
#define REDUCE_DIM {dim}
{chr(10).join(f'#include "{h}"' for h in compute_headers(row, new))}
{entry} {{
    uint32_t num_tiles = get_arg_val<uint32_t>(0);
    constexpr auto c0 = tt::CBIndex::c_0;
    constexpr auto c1 = tt::CBIndex::c_1;
    constexpr auto c16 = tt::CBIndex::c_{OUT_CB};
    compute_kernel_hw_startup(c0, c1, c16);
    {init};
    cb_wait_front(c1, 1);
    cb_reserve_back(c16, 1);
    tile_regs_acquire();
    for (uint32_t i = 0; i < num_tiles; ++i) {{
        cb_wait_front(c0, 1);
        {spelled(row["call"], new)};
        cb_pop_front(c0, 1);
    }}
    tile_regs_commit();
    tile_regs_wait();
    pack_tile(0, c16);
    tile_regs_release();
    cb_push_back(c16, 1);
    cb_pop_front(c1, 1);
    reduce_uninit();
}}
{close}
"""


def compute(row: Json, new: bool) -> str:
    """The compute kernel of ``row`` for tt-metal 0.8x (``new``) or 0.6x."""
    if row["kind"] == "matmul":
        return matmul_compute(row, new)
    if row["kind"] == "reduction":
        return reduction_compute(row, new)
    includes = "\n".join(f'#include "{h}"' for h in compute_headers(row, new))
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


def unpack_mode(module: ModuleType) -> "type[ttnn.UnpackToDestMode]":
    """``UnpackToDestMode``: tt-metal 0.6x binds it only in the program-descriptor module, 0.8x at the top too."""
    try:
        return cast("type[ttnn.UnpackToDestMode]", module.UnpackToDestMode)
    except AttributeError:
        return cast("type[ttnn.UnpackToDestMode]", module._ttnn.program_descriptor.UnpackToDestMode)


def source_code(module: ModuleType) -> "ttnn.SourceType":
    """The inline-source kernel type: nested in ``KernelDescriptor`` in tt-metal 0.8x, a module enum in 0.6x."""
    try:
        return cast("ttnn.SourceType", module.KernelDescriptor.SourceType.SOURCE_CODE)
    except AttributeError:
        return cast("ttnn.SourceType", module._ttnn.program_descriptor.SourceType.SOURCE_CODE)


def runtime_args(module: ModuleType, values: list[int]) -> object:
    """``values`` as the runtime arguments of core (0, 0): a ``RuntimeArgs`` in tt-metal 0.8x, nested lists
    indexed ``[x][y]`` in 0.6x."""
    try:
        args = module.RuntimeArgs()
    except AttributeError:
        return [[values]]
    args[0][0] = values
    return args


def inputs(row: Json) -> list["torch.Tensor"]:
    """Operands drawn from the row's domain ``[lo, hi]``, every element distinct, shaped as TILES tiles."""
    import torch

    lo, hi = row["domain"]
    count = 1 if row["kind"] in ("unary", "fill") else 2
    base = torch.linspace(lo, hi, TILES * TILE, dtype=torch.float32)
    if row["kind"] == "matmul":  # A is one row of TILES K tiles (32 x 32 TILES), B one column of them
        return [base.reshape(32, TILES * 32), base.roll(97).reshape(TILES * 32, 32)]
    if row["kind"] == "reduction":  # the data tiles and the scaler tile: 1 in the first row of each 16 x 16 face
        scaler = torch.zeros(32, 32)
        scaler[0::16] = 1.0
        return [base.reshape(TILES * 32, 32), scaler]
    return [base.roll(k * 97).reshape(TILES * 32, 32) for k in range(count)]


def dest_fp32(row: Json) -> bool:
    """Whether DST accumulates in fp32: for f32 rows, and for every matrix product and reduction, whose sum over
    tiles loses digits in a 16-bit accumulator (bf16 mma measured 7% on ttsim without it). ``ask`` hands out the
    same setting."""
    return row["dtype"] == "f32" or row["kind"] in ("matmul", "reduction")


def filled(call: str) -> float:
    """The value a ``fill_tile(dst, value)`` call writes."""
    found = re.search(r",\s*([-+0-9.eE]+)f?\s*\)", call)
    if found is None:
        raise ValueError(f"a fill call names its value: {call}")
    return float(found.group(1))


def reference(op: str, xs: list["torch.Tensor"], call: str = "") -> "torch.Tensor":
    import torch

    x = xs[0].double()
    if op == "broadcast":
        return torch.full_like(x, filled(call))
    unary = {
        "exp": torch.exp, "log": torch.log, "sqrt": torch.sqrt, "rsqrt": torch.rsqrt, "recip": torch.reciprocal,
        "abs": torch.abs, "neg": torch.neg, "tanh": torch.tanh, "sin": torch.sin, "cos": torch.cos,
    }  # fmt: skip
    if op in unary:
        return unary[op](x)
    if op == "scan_add":  # down each column, across the tiles of that column
        return torch.cumsum(x, dim=0)
    if op in ("reduce_add", "reduce_max"):  # REDUCE_SCALAR: one value for every element of every tile
        return x.sum() if op == "reduce_add" else x.max()
    y = xs[1].double()
    if op == "mma":  # apart from the elementwise rows, whose tiles do not chain as a product
        return x @ y
    return {"add": x + y, "sub": x - y, "mul": x * y, "div": x / y, "max": torch.maximum(x, y)}[op]


def run(dev: "ttnn.MeshDevice", row: Json, new: bool) -> Json:
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
    matmul = row["kind"] == "matmul"
    one_tile = matmul or row["kind"] == "reduction"  # the output is one tile
    shape = [32, 32] if one_tile else list(xs[0].shape)
    out = ttnn.allocate_tensor_on_device(ttnn.Shape(shape), tt_dtype, ttnn.TILE_LAYOUT, dev, memory)
    cbs = [
        ttnn.CBDescriptor(
            total_size=2 * page,
            core_ranges=core,
            format_descriptors=[ttnn.CBFormatDescriptor(buffer_index=i, data_format=tt_dtype, page_size=page)],
        )
        for i in [*range(len(xs)), OUT_CB]
    ]
    reader_args = runtime_args(ttnn, [TILES, *(t.buffer_address() for t in tensors)])
    writer_args = runtime_args(ttnn, [1 if one_tile else TILES, out.buffer_address()])
    compute_args = runtime_args(ttnn, [TILES])
    per_input = [list(ttnn.TensorAccessorArgs(t).get_compile_time_args()) for t in tensors]
    offsets = [sum(len(a) for a in per_input[:k]) for k in range(len(per_input))]
    config = ttnn.ComputeConfigDescriptor()
    config.fp32_dest_acc_en = dest_fp32(row)
    config.math_approx_mode = False
    config.math_fidelity = ttnn.MathFidelity.HiFi4  # LoFi, the default, multiplies with truncated mantissas
    if row["dtype"] == "f32" and row["kind"] not in (
        "binary",
        "matmul",
        "reduction",
    ):  # FPU operands unpack to SrcA/SrcB (TF32): only DST takes FP32
        # one mode per circular buffer: tt-metal 0.6x has 32 of them, 0.8x has 64
        config.unpack_to_dest_mode = [unpack_mode(ttnn).UnpackToDestFp32] * (64 if new else 32)
    source = source_code(ttnn)
    kernels = [
        ttnn.KernelDescriptor(
            kernel_source=reader(offsets, new, 1 if row["kind"] == "reduction" else -1), source_type=source, core_ranges=core,
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
    want = reference(row["op"], [x.float() for x in xs], spelled(row["call"], new))
    if row["kind"] == "reduction":  # REDUCE_SCALAR leaves the value at face 0 [0, 0] and zeros elsewhere
        got, want = got[0, 0].reshape(1), want.reshape(1)
    if matmul:  # a sum of products: its error is relative to the result's scale, not to each element
        rel = ((got.double() - want).abs().max() / want.abs().max()).item()
    else:
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
