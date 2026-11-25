# Copyright 2026 ETH Zurich and the Alloy authors.
"""The default Tensix collectives: Bcast, Allgather, Gather, Scatter and Alltoall of the shared gate's in-kernel form
(rank c loads row c of X, runs the collective, stores its output to row c of Y; root 0), each one dataflow kernel per
rank that moves whole tiles and computes nothing.

Rank p runs on logical core (p, 0). A rank reads its X row from DRAM into CB 0 and writes its output from CB 1 to its
Y row. Between ranks the data moves over the NoC into the receiver's CB 1 (every core has its CBs at the same L1
address), and semaphore 0 counts what has arrived:
- Bcast multicasts the root's row to the other ranks and sets their semaphores by multicast;
- Allgather, Gather, Scatter and Alltoall write each block to its receiver (a rank's own block too, a NoC write to
  itself) and raise the receiver's semaphore by one; a receiver waits for its count.

The row's load and store are the copy and wait nodes of :mod:`alloy.tensixgen.movement`, as in the split's tile
bodies: ``read_row`` is the X copy and its read :class:`~alloy.tensixgen.movement.NocWait`, ``write_row`` the Y copy
and its write wait. The circular-buffer syncs stay unspelled: the one dataflow kernel has no compute kernel to hand
tiles to.

Collectives that combine data (Reduce, Allreduce, ReduceScatter) need the compute kernel and are refused, as is a row
that is not whole tiles. Moving data more cleverly (overlap, pipelined multicast trees) is the agent's job.
"""

import dace
from dace.libraries.comm.nodes import Allgather, Alltoall, Bcast, Gather, Scatter
from dace.libraries.comm.nodes.node import CommNode

from alloy.isa.tensix_harness import dataflow_include
from alloy.jsontype import Json
from alloy.tensixgen import movement
from alloy.tensixgen.backend import Refused
from alloy.tensixgen.split import Program

TILE = 1024

#: The body of each collective after the prologue: ``in``, ``out`` are CB 0 and CB 1, ``bytes`` a tile, ``IN`` and
#: ``OUT`` the tiles of an X row and a Y row, ``P`` the ranks.
BODIES: dict[type[CommNode], str] = {
    Bcast: """
    if (rank == 0) {
        read_row(0);
        noc_async_write(in, get_noc_addr(core_x(0), core_y(0), out), OUT * bytes);
        if (P > 1) {
            noc_async_write_multicast(in, get_noc_multicast_addr(mx0, my0, mx1, my1, out), OUT * bytes, P - 1);
        }
        noc_async_write_barrier();
        *sem = 1;
        if (P > 1) {
            noc_semaphore_set_multicast(sem_addr, get_noc_multicast_addr(mx0, my0, mx1, my1, sem_addr), P - 1);
        }
        noc_async_write_barrier();
    }
    noc_semaphore_wait(sem, 1);
    write_row();""",
    Allgather: """
    read_row(rank);
    for (uint32_t p = 0; p < P; ++p) send(in, p, out + rank * IN * bytes, IN * bytes);
    noc_async_write_barrier();
    for (uint32_t p = 0; p < P; ++p) signal(p);
    noc_semaphore_wait(sem, P);
    write_row();""",
    Gather: """
    read_row(rank);
    send(in, 0, out + rank * IN * bytes, IN * bytes);
    noc_async_write_barrier();
    signal(0);
    if (rank == 0) {
        noc_semaphore_wait(sem, P);
        write_row();
    }""",
    Scatter: """
    if (rank == 0) {
        read_row(0);
        for (uint32_t p = 0; p < P; ++p) send(in + p * OUT * bytes, p, out, OUT * bytes);
        noc_async_write_barrier();
        for (uint32_t p = 0; p < P; ++p) signal(p);
    }
    noc_semaphore_wait(sem, 1);
    write_row();""",
    Alltoall: """
    read_row(rank);
    constexpr uint32_t block = OUT / P;  // tiles rank r sends rank p, to slot r of p's row
    for (uint32_t p = 0; p < P; ++p) send(in + p * block * bytes, p, out + rank * block * bytes, block * bytes);
    noc_async_write_barrier();
    for (uint32_t p = 0; p < P; ++p) signal(p);
    noc_semaphore_wait(sem, P);
    write_row();""",
}


def comm_node(sdfg: dace.SDFG) -> CommNode | None:
    """The SDFG's one collective, or None when it has none."""
    found = [n for n, _ in sdfg.all_nodes_recursive() if isinstance(n, CommNode)]
    if len(found) > 1:
        raise Refused(f"{sdfg.name}: {len(found)} collectives; a Tensix collective program runs one")
    return found[0] if found else None


def kernel(node: CommNode, moves: movement.Movement, ranks: int, in_tiles: int, out_tiles: int, new: bool) -> str:
    """The one dataflow kernel every rank runs. Runtime args: rank, X and Y addresses, the multicast rectangle of
    ranks 1..P-1, then each rank's virtual NoC coordinates."""
    return f"""// {type(node).__name__} over {ranks} ranks: an X row is {in_tiles} tiles, a Y row {out_tiles} (alloy.tensixgen.collectives)
#include <stdint.h>
#include "{dataflow_include(new)}"

constexpr uint32_t P = {ranks}, IN = {in_tiles}, OUT = {out_tiles};

void kernel_main() {{
    const uint32_t rank = get_arg_val<uint32_t>(0);
    const uint32_t mx0 = get_arg_val<uint32_t>(3), my0 = get_arg_val<uint32_t>(4);
    const uint32_t mx1 = get_arg_val<uint32_t>(5), my1 = get_arg_val<uint32_t>(6);
    auto core_x = [](uint32_t p) {{ return get_arg_val<uint32_t>(7 + 2 * p); }};
    auto core_y = [](uint32_t p) {{ return get_arg_val<uint32_t>(8 + 2 * p); }};
    constexpr auto xargs = TensorAccessorArgs<0>();
    constexpr auto yargs = TensorAccessorArgs<xargs.next_compile_time_args_offset()>();
    const uint32_t bytes = get_tile_size(0);
    const auto xs = TensorAccessor(xargs, get_arg_val<uint32_t>(1), bytes);
    const auto ys = TensorAccessor(yargs, get_arg_val<uint32_t>(2), bytes);
    const uint32_t in = get_write_ptr(0), out = get_write_ptr(1);
    const uint32_t sem_addr = get_semaphore(0);
    volatile tt_l1_ptr uint32_t* sem = reinterpret_cast<volatile tt_l1_ptr uint32_t*>(sem_addr);
    // X row r into CB 0, Y row rank from CB 1
    auto read_row = [&](uint32_t r) {{
        for (uint32_t t = 0; t < IN; ++t) noc_async_read_tile(r * IN + t, xs, in + t * bytes);
        {moves.read_wait.call()}
    }};
    auto write_row = [&]() {{
        for (uint32_t t = 0; t < OUT; ++t) noc_async_write_tile(rank * OUT + t, ys, out + t * bytes);
        {moves.write_wait.call()}
    }};
    auto send = [&](uint32_t src, uint32_t p, uint32_t dst, uint32_t size) {{
        noc_async_write(src, get_noc_addr(core_x(p), core_y(p), dst), size);
    }};
    auto signal = [&](uint32_t p) {{ noc_semaphore_inc(get_noc_addr(core_x(p), core_y(p), sem_addr), 1); }};
{BODIES[type(node)]}
}}
"""


def program(task: Json, sdfg: dace.SDFG, node: CommNode, version: str = "v08") -> Program:
    """The Tensix program of a gate collective: X (P, in) and Y (P, out) float32, both rows whole tiles."""
    if type(node) not in BODIES:
        raise Refused(f"{node.label}: {type(node).__name__} combines data, which needs the compute kernel; the "
                      "default Tensix collectives only move tiles")  # fmt: skip
    shapes = {name: sdfg.arrays[name].shape for name in ("X", "Y")}
    ranks, in_cols = (int(s) for s in shapes["X"])
    out_cols = int(shapes["Y"][1])
    if in_cols % TILE or out_cols % TILE:
        raise Refused(f"{node.label}: rows of {in_cols} and {out_cols} floats; a Tensix collective moves whole tiles")
    descriptor: dict[str, object] = {
        **task,
        "collective": {"ranks": ranks},
        "placement": {},
        "options": {"cores": ranks},
    }
    (state,) = [s for n, s in sdfg.all_nodes_recursive() if n is node]
    assert isinstance(state, dace.SDFGState)
    moves = movement.insert(state, ["X"], "Y")
    source = kernel(node, moves, ranks, in_cols // TILE, out_cols // TILE, version == "v08")
    return Program(task["name"], source, "", "", {}, descriptor)
