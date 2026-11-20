# Copyright 2026 ETH Zurich and the Alloy authors.
"""Probe of per-channel HBM sections on the v1 model: python -m alloy.softhiergen.gate.hbm_probe <folder>, then run build_run.sh there.

Each HBM node after the first gets its own ELF section and load segment at its node base (``.dsh_hbm<k>``); node 0 is
the SDK's ``.hbm``. The program checks that
GVSoC preloads every node, and that every cluster's DMA reads and writes every node, with the cycles of one 4 KiB read.

Result 2026-11-20 (ault job 920009, v1 image): nodes west0 0xC0000000, west1 0xC4000000, south0 0xD8000000 and south1
0xDC000000 all preload, and every cluster reads and writes each of them correctly; a 4 KiB read takes 99-122 cycles
from every cluster to every node.
"""

import pathlib
import shutil
import sys

from alloy.softhiergen.arch import TARGET, V1, node_bases
from alloy.softhiergen.program import FLAGS, RUNTIME

WORDS = 1024


def main_c(nodes: list[tuple[str, int]]) -> str:
    arrays = []
    for k, _ in enumerate(nodes):
        body = ", ".join(f"0x{(k << 16) | i:x}u" for i in range(WORDS))
        section = ".hbm" if k == 0 else f".dsh_hbm{k}"
        arrays.append(f'__attribute__((section("{section}"), aligned(64))) uint32_t node{k}[{2 * WORDS}] = {{{body}}};')
    table = ", ".join(f"node{k}" for k in range(len(nodes)))
    names = ", ".join(f'"{name}"' for name, _ in nodes)
    return f"""#include <stdint.h>
#include "flex_printf.h"
#include "softhiergen/dsh_rt.c"

{chr(10).join(arrays)}

static uint32_t* const nodes[] = {{{table}}};
static const char* const names[] = {{{names}}};
static uint32_t buffer[{WORDS}] __attribute__((section(".l1"), aligned(64)));
static uint32_t result[2] __attribute__((section(".l1")));

static inline uint32_t cycles(void) {{
    uint32_t value;
    asm volatile("csrr %0, mcycle" : "=r"(value));
    return value;
}}

// Every cluster in turn: per node, read the preloaded words and write its own slice of the node's second half
int main(void) {{
    flex_barrier_xy_init();
    flex_global_barrier_xy();
    uint32_t me = flex_get_cluster_id();
    for (uint32_t turn = 0; turn < ARCH_NUM_CLUSTER; ++turn) {{
        for (uint32_t k = 0; k < {len(nodes)}; ++k) {{
            if (turn == me) {{
                if (flex_is_dm_core()) {{
                    uint32_t start = cycles();
                    flex_dma_async_1d(dsh_addr(buffer), dsh_addr(nodes[k]), sizeof(buffer));
                    flex_dma_async_wait_all();
                    result[1] = cycles() - start;
                }}
                flex_intra_cluster_sync();
                if (flex_is_first_core()) {{
                    uint32_t bad = 0;
                    for (uint32_t i = 0; i < {WORDS}; ++i) bad += buffer[i] != ((k << 16) | i);
                    printf("PROBE read cluster %u node %s base %x bad %u cycles %u\\n", me, names[k],
                           (uint32_t)(uintptr_t)nodes[k], bad, result[1]);
                    for (uint32_t i = 0; i < 64; ++i) buffer[i] = 0xA0000000u | (me << 20) | (k << 16) | i;
                }}
                flex_intra_cluster_sync();
                if (flex_is_dm_core()) {{
                    flex_dma_async_1d(dsh_addr(nodes[k] + {WORDS} + me * 64), dsh_addr(buffer), 64 * 4);
                    flex_dma_async_wait_all();
                }}
                flex_intra_cluster_sync();
            }}
            flex_global_barrier_xy();
        }}
    }}
    if (me == 0) {{
        for (uint32_t k = 0; k < {len(nodes)}; ++k) {{
            if (flex_is_dm_core()) {{
                flex_dma_async_1d(dsh_addr(buffer), dsh_addr(nodes[k] + {WORDS}), ARCH_NUM_CLUSTER * 64 * 4);
                flex_dma_async_wait_all();
            }}
            flex_intra_cluster_sync();
            if (flex_is_first_core()) {{
                uint32_t bad = 0;
                for (uint32_t c = 0; c < ARCH_NUM_CLUSTER; ++c)
                    for (uint32_t i = 0; i < 64; ++i) bad += buffer[c * 64 + i] != (0xA0000000u | (c << 20) | (k << 16) | i);
                printf("PROBE write node %s bad %u\\n", names[k], bad);
            }}
            flex_intra_cluster_sync();
        }}
    }}
    flex_global_barrier_xy();
    flex_eoc(0);
    return 0;
}}
"""


def build_run(nodes: list[tuple[str, int]]) -> str:
    # Node 0 is the SDK's .hbm, which starts at the first west node after .data
    phdrs = "\\n".join(f"  dsh_hbm{k} PT_LOAD;" for k in range(1, len(nodes)))
    sections = "\\n".join(
        f"  .dsh_hbm{k} 0x{base:x} : {{ KEEP(*(.dsh_hbm{k})) }} :dsh_hbm{k}" for k, (_, base) in enumerate(nodes) if k
    )
    return f"""#!/bin/bash
# The SDK linker script plus one load segment and section per HBM node after the first
set -eo pipefail
cd "$(dirname "$0")"
SDK=$SOFTHIER_SDK/runtime/runtime
awk -v phdrs="{phdrs}" -v sections="{sections}" '
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
' $SDK/flex_memory.ld > link.ld
riscv32-unknown-elf-gcc {FLAGS} -I $SDK/include -I include -T link.ld -nostartfiles -Wl,--gc-sections \\
    -o softhier.elf $SDK/flex_start.s main.c
riscv32-unknown-elf-readelf -lW softhier.elf | grep LOAD
SOFTHIER_ARCH_FILE=$PWD/arch.py timeout 1800 gvsoc --target={TARGET} --binary softhier.elf --work-dir $PWD run \\
    > gvsoc.out 2>&1 || echo "gvsoc exit $?"
grep PROBE gvsoc.out
"""


def write(folder: pathlib.Path) -> None:
    nodes = node_bases()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "main.c").write_text(main_c(nodes))
    (folder / "arch.py").write_text(V1.to_arch_py())
    shutil.copytree(RUNTIME, folder / "include", dirs_exist_ok=True)
    script = folder / "build_run.sh"
    script.write_text(build_run(nodes))
    script.chmod(0o755)


if __name__ == "__main__":
    write(pathlib.Path(sys.argv[1]))
