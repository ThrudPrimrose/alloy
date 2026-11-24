# Copyright 2026 ETH Zurich and the Alloy authors.
"""Build a lowered SDFG into a SoftHier program folder, and read its results after GVSoC has run it.

A folder holds ``kernels.cpp`` (the generated unit), ``main.c`` (the program's arrays as preloaded ``.hbm`` data, a
placed array as one share per HBM node in the node's section, and ``main``: the SDK frame around ``__dsh_program``, a
cycle count, and a dump of every array), the runtime headers and ``build_run.sh``, which compiles with the SDK's flags,
links with its start code and linker script (plus a section per HBM node when arrays are placed), and runs GVSoC.

shortcut: inputs are baked into the ELF, so new data means a relink; preload separately when programs get large.
"""

import json
import pathlib
import shutil
from collections.abc import Mapping
from typing import Any

import numpy
from dace import config, data, dtypes
from dace.sdfg import SDFG

from alloy.softhiergen import hbm, passes, storage
from alloy.softhiergen.arch import TARGET, V1, node_bases
from alloy.softhiergen.codegen.target import SoftHierCodeGen, static_size
from alloy.softhiergen.library import rvv

RUNTIME = pathlib.Path(__file__).parent / "runtime" / "include"

#: A program's arguments by name: an array, or a NumPy scalar for a scalar argument.
Inputs = Mapping[str, numpy.ndarray | numpy.generic]

#: The SDK's compile flags (runtime/CMakeLists.txt) with zvfh, as Alloy's rows build, without -ffast-math: it lets GCC
#: assume no NaN or infinity.
FLAGS = (
    "-mabi=ilp32d -mcmodel=medlow -march=rv32imafdv_zfh_zvfh -O3 -fno-builtin -fno-tree-vectorize "
    "-fno-common -ffunction-sections"
)
CXX_FLAGS = "-std=c++17 -fno-exceptions -fno-rtti -fno-threadsafe-statics -fno-use-cxa-atexit -ffreestanding"
#: The TCDM buffer main dumps arrays through, in 32-bit words.
DUMP_WORDS = 4096

BUILD_RUN = f"""#!/bin/bash
# Builds and runs the program in this folder: SOFTHIER_SDK set, the toolchain on PATH; `build` skips the run.
set -eo pipefail
cd "$(dirname "$0")"
SDK=$SOFTHIER_SDK/runtime/runtime
riscv32-unknown-elf-g++ {FLAGS} {CXX_FLAGS} -I include -c kernels.cpp -o kernels.o
riscv32-unknown-elf-gcc {FLAGS} -I $SDK/include -I include -c main.c -o main.o
riscv32-unknown-elf-gcc {FLAGS} -I $SDK/include -T $SDK/flex_memory.ld -nostartfiles -Wl,--gc-sections \\
    -o softhier.elf $SDK/flex_start.s main.o kernels.o -lm
# The linker script's regions are larger than the memories: everything linked to L3 must fit the instruction memory,
# .l1 the TCDM from its origin 0x10
riscv32-unknown-elf-size -A softhier.elf | awk -v base={V1.instruction_mem_base} -v code={V1.instruction_mem_size} \\
    -v hbm={V1.hbm_start_base} -v l1={V1.cluster_tcdm_size - 0x10} '
    $3 !~ /^[0-9]+$/ {{ next }}
    $1 == ".l1" && $2 > l1 {{ print ".l1 holds " $2 " bytes, the TCDM " l1; bad = 1 }}
    $3 >= base && $3 < hbm && $3 + $2 - base > code {{
        print $1 " ends " $3 + $2 - base " bytes in, the instruction memory holds " code; bad = 1
    }}
    END {{ exit bad }}'
echo DSH-BUILT
[ "$1" = build ] && exit 0
SOFTHIER_ARCH_FILE=$PWD/arch.py timeout 1800 gvsoc --target={TARGET} --binary softhier.elf --work-dir $PWD run \\
    > gvsoc.out 2>&1
echo DSH-RAN
"""


def link_script(nodes: int) -> str:
    """Shell lines that write ``link.ld``: the SDK's linker script plus a load segment and a section at the node's
    base for each of the first ``nodes`` HBM nodes after node 0, which is the SDK's ``.hbm``."""
    bases = node_bases()[1:nodes]
    phdrs = "\\n".join(f"  dsh_hbm{k} PT_LOAD;" for k in range(1, nodes))
    sections = "\\n".join(
        f"  .dsh_hbm{k} 0x{base:x} : {{ KEEP(*(.dsh_hbm{k})) }} :dsh_hbm{k}" for k, (_, base) in enumerate(bases, 1)
    )
    return f"""awk -v phdrs="{phdrs}" -v sections="{sections}" '
    /^PHDRS/ {{ in_phdrs = 1 }}
    in_phdrs && /^}}/ {{ phdrs_end = NR; in_phdrs = 0 }}
    {{ lines[NR] = $0 }}
    /^}}/ {{ last = NR }}
    END {{
        for (i = 1; i <= NR; ++i) {{
            if (i == phdrs_end) print phdrs
            if (i == last) print sections
            print lines[i]
        }}
    }}
' $SDK/flex_memory.ld > link.ld"""


def build_run(nodes: int) -> str:
    """``build_run.sh`` for a program whose placed arrays span ``nodes`` HBM nodes (1: only ``.hbm``)."""
    if nodes <= 1:
        return BUILD_RUN
    script = BUILD_RUN.replace("-T $SDK/flex_memory.ld", "-T link.ld")
    return script.replace(
        "SDK=$SOFTHIER_SDK/runtime/runtime\n", f"SDK=$SOFTHIER_SDK/runtime/runtime\n{link_script(nodes)}\n"
    )


def generate(sdfg: SDFG, tile: int = 256) -> str:
    """Lowers ``sdfg`` in place and returns the generated C++ unit."""
    passes.lower(sdfg, tile)
    with config.set_temporary("compiler", "cpu", "explicit_copy", value=False):
        objects = sdfg.generate_code()
    return str(next(obj.clean_code for obj in objects if obj.target is SoftHierCodeGen))


def scalar_literal(value: numpy.generic) -> str:
    """The C literal of exactly ``value`` (a float as a hex literal)."""
    if isinstance(value, numpy.floating):
        if numpy.isnan(value):
            raise ValueError("a NaN input has no C literal that keeps its bits")
        if numpy.isinf(value):
            return "-__builtin_inf()" if value < 0 else "__builtin_inf()"
        return float(value).hex() + ("f" if value.itemsize <= 4 else "")
    return str(int(value))


def c_type(dtype: dtypes.typeclass) -> str:
    """The C spelling of an element type; DaCe spells float16 as C++ (``dace::float16``)."""
    return "_Float16" if dtype == dtypes.float16 else dtype.ctype


def placed_shares(
    name: str, desc: data.Array, array: numpy.ndarray, constants: Mapping[str, Any]
) -> tuple[list[str], list[str], numpy.ndarray]:
    """The placed array ``name`` holding ``array`` as one C array per node in the node's section, the dump calls of
    the shares in node order, and each element's position in the shares laid end to end."""
    positions = hbm.positions(desc, constants)
    share = hbm.share_size(desc, constants)
    shares = numpy.zeros(hbm.node_count(name, desc, constants) * share, dtype=array.dtype)
    shares[positions] = array.ravel()
    lines, dumps = [], []
    for node in range(len(shares) // share):
        body = ", ".join(scalar_literal(value) for value in shares[node * share : (node + 1) * share])
        lines.append(
            f'__attribute__((section("{hbm.section(node)}"), aligned(64))) {c_type(desc.dtype)} '
            f"{hbm.share_name(name, node)}[{share}] = {{{body}}};"
        )
        dumps.append(f'        dump("{name}", {hbm.share_name(name, node)}, {share * array.itemsize});')
    return lines, dumps, positions


def main_unit(sdfg: SDFG, inputs: Inputs) -> tuple[str, list[dict[str, Any]]]:
    """``main.c`` and the metadata of the arrays it dumps, in dump order."""
    data_lines, dumps, meta = [], [], []
    for name, desc in sdfg.arrays.items():
        if desc.transient:
            continue
        if isinstance(desc, data.Scalar):
            value = desc.dtype.as_numpy_dtype().type(inputs[name])
            data_lines.append(f"const {c_type(desc.dtype)} {name} = {scalar_literal(value)};")
            continue
        array = numpy.zeros(desc.shape, dtype=desc.dtype.as_numpy_dtype())
        if name in inputs:
            array[...] = inputs[name]
        if desc.placement is not None:
            lines, calls, positions = placed_shares(name, desc, array, sdfg.constants)
            data_lines += lines
            dumps += calls
            meta.append(
                {"name": name, "dtype": array.dtype.str, "shape": list(array.shape), "positions": positions.tolist()}
            )
            continue
        body = ", ".join(scalar_literal(value) for value in array.flat)
        data_lines.append(
            f'__attribute__((section(".hbm"), aligned(64))) {c_type(desc.dtype)} {name}[{array.size}] = {{{body}}};'
        )
        dumps.append(f'        dump("{name}", {name}, {array.nbytes});')
        meta.append({"name": name, "dtype": array.dtype.str, "shape": list(array.shape)})
    source = f"""#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "flex_printf.h"
// The SDK headers define their functions: the runtime and main share this one C unit
#include "softhiergen/dsh_rt.c"
#include "softhiergen/dsh_ladder.c"

_Static_assert(ARCH_NUM_CLUSTER == {V1.num_clusters}, "the SDK header and alloy.softhiergen.arch.V1 differ in cluster count");

void __dsh_program(void);

{chr(10).join(data_lines)}

static uint32_t dump_buffer[{DUMP_WORDS}] __attribute__((section(".l1"), aligned(64)));

static inline uint32_t cycles(void) {{
    uint32_t value;
    asm volatile("csrr %0, mcycle" : "=r"(value));
    return value;
}}

// The DMA core brings an HBM array into TCDM piece by piece; core 0 prints its 32-bit words
static void dump(const char* name, const void* array, uint32_t bytes) {{
    for (uint32_t offset = 0; offset < bytes; offset += sizeof(dump_buffer)) {{
        uint32_t size = bytes - offset < sizeof(dump_buffer) ? bytes - offset : sizeof(dump_buffer);
        if (flex_is_dm_core()) {{
            flex_dma_async_1d(dsh_addr(dump_buffer), dsh_addr((const uint8_t*)array + offset), size);
            flex_dma_async_wait_all();
        }}
        flex_intra_cluster_sync();
        if (flex_is_first_core())
            for (uint32_t i = 0; i < (size + 3) / 4; ++i) printf("DSH %s %x\\n", name, dump_buffer[i]);
        flex_intra_cluster_sync();
    }}
}}

int main(void) {{
    flex_barrier_xy_init();
    flex_global_barrier_xy();
    uint32_t start = 0;
    int timer = flex_get_cluster_id() == 0 && flex_get_core_id() == 0;
    if (timer) {{
        flex_timer_start();
        start = cycles();
    }}
    __dsh_program();
    flex_global_barrier_xy();
    if (timer) {{
        uint32_t end = cycles();
        flex_timer_end();
        printf("DSH-CYCLES %u\\n", end - start);
    }}
    flex_global_barrier_xy();
    if (flex_get_cluster_id() == 0) {{
{chr(10).join(dumps)}
    }}
    flex_global_barrier_xy();
    flex_eoc(0);
    return 0;
}}
"""
    return source, meta


def write_folder(folder: pathlib.Path, sdfg: SDFG, kernels: str, inputs: Inputs) -> None:
    """Writes the program folder of a lowered ``sdfg`` whose generated unit is ``kernels``."""
    # An array without a placement goes to .hbm from the first west channel on
    west = V1.hbm_chan_placement[0] * V1.hbm_node_addr_space
    hbm_arrays = {
        name: desc for name, desc in sdfg.arrays.items() if isinstance(desc, data.Array) and desc.storage == storage.HBM
    }
    used = sum(
        -(-static_size(desc, name) * desc.dtype.bytes // 64) * 64
        for name, desc in hbm_arrays.items()
        if desc.placement is None  # pyright: ignore[reportUnnecessaryComparison] -- DaCe's annotation
    )
    if used > west:
        raise ValueError(f"{sdfg.name}: its HBM arrays take {used} bytes, the west HBM channels hold {west}")
    # Each node holds its shares of the placed arrays; node 0 also the .hbm arrays
    per_node = [used] + [0] * (len(node_bases()) - 1)
    for name, desc in hbm_arrays.items():
        if desc.placement is not None:  # pyright: ignore[reportUnnecessaryComparison] -- DaCe's annotation
            for node in range(hbm.node_count(name, desc, sdfg.constants)):
                per_node[node] += hbm.share_size(desc, sdfg.constants) * desc.dtype.bytes
    nodes = max((node + 1 for node, size in enumerate(per_node) if size), default=1)
    if nodes > 1 and max(per_node) > V1.hbm_node_addr_space:
        raise ValueError(f"{sdfg.name}: its HBM nodes hold {per_node} bytes, one node {V1.hbm_node_addr_space}")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "kernels.cpp").write_text(kernels)
    source, meta = main_unit(sdfg, inputs)
    (folder / "main.c").write_text(source)
    (folder / "meta.json").write_text(json.dumps(meta))
    (folder / "arch.py").write_text(V1.to_arch_py())
    shutil.copytree(RUNTIME, folder / "include", dirs_exist_ok=True)
    (folder / "include" / "softhiergen" / "dsh_ladder.c").write_text(rvv.ladder_unit())
    script = folder / "build_run.sh"
    script.write_text(build_run(nodes))
    script.chmod(0o755)


def read_results(folder: pathlib.Path) -> tuple[dict[str, numpy.ndarray], int]:
    """The arrays ``main`` dumped and the cycles of ``__dsh_program`` on cluster 0, core 0."""
    text = (folder / "gvsoc.out").read_text()
    found: dict[str, list[int]] = {}
    cycles = -1
    for line in text.splitlines():
        parts = line.split()
        if line.startswith("DSH ") and len(parts) == 3:
            found.setdefault(parts[1], []).append(int(parts[2], 16))
        elif line.startswith("DSH-CYCLES "):
            cycles = int(parts[1])
    arrays = {}
    for entry in json.loads((folder / "meta.json").read_text()):
        dtype = numpy.dtype(entry["dtype"])
        raw = numpy.array(found.get(entry["name"], []), dtype=numpy.uint32).tobytes()
        # A placed array was dumped share by share: its elements sit at their positions in the shares
        positions = numpy.array(entry["positions"]) if "positions" in entry else None
        count = int(numpy.prod(entry["shape"])) if positions is None else int(positions.max()) + 1
        if len(raw) < count * dtype.itemsize:
            raise ValueError(f"{entry['name']}: the run printed {len(raw)} bytes of {count * dtype.itemsize}")
        values = numpy.frombuffer(raw[: count * dtype.itemsize], dtype=dtype)
        arrays[entry["name"]] = (values if positions is None else values[positions]).reshape(entry["shape"])
    return arrays, cycles
