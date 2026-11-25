# Tile backends: softhiergen and tensixgen

Alloy generates code for two tile accelerators from one DaCe SDFG: SoftHier v1 (`alloy/softhiergen/`, simulated on
GVSoC) and Tenstorrent Tensix (`alloy/tensixgen/`, simulated on ttsim). Both backends generate a naive baseline. It
is correct and checked against NumPy, and it moves data only in the program's own order: one tile from global
memory to a core, the tile computed, the result written back. Overlapping transfers with compute, multicast trees,
and keeping data on chip across kernels are left to the agent. The lookup (`alloy ask softhier ...`,
`alloy ask tensix ...`) gives the agent the asynchronous steps for this, each with the wait that completes it.

This page lists what the two backends share, where they differ, and what each refuses. The SoftHier internals are in
[softhiergen.md](softhiergen.md).

## 1. What both share

| Part | Where | What it does |
|---|---|---|
| Entry | `alloy.tilelower.lower(sdfg, target, scalars, name)` | Lowers the SDFG in place for `"softhier"` or `"tensix"` and returns the generated sources: SoftHier's C++ unit, or Tensix's reader, compute, and writer kernels. Tensix reads its task off the SDFG: the non-transient arrays read, the one array written, and map or reduce by that array's size. Both gates lower through it. |
| Front | `alloy.tilelower.front(sdfg, width, fuse_multiply_add)` | Substitutes the specialized sizes into the SDFG, expands `numpy.where` to an elementwise map, then runs `simplify` without dead-dataflow elimination, vertical map fusion, and redundant-array removal. Then DaCe's vectorizer turns each elementwise map into a map of tile nodes, `width` lanes wide. |
| Refusal | `alloy.tilelower.Unsupported` | The base class of softhiergen's `LoweringError` and tensixgen's `Refused`. The message names the node and the reason. Neither backend falls back to a scalar loop it was not built for. |
| Gate | `alloy.gate`, cases in `alloy/softhiergen/gate/programs.py` (`all_cases`, with the CloudSC nests of `cloudsc.py`) | Holds the NumPy programs, their inputs, and their float64 references. The check is per element: `\|out - ref\| <= tol (\|ref\| + max \|ref\|)`, with integer and bool outputs exact. Each backend also runs one planted wrong program (vector add with the add swapped for a sub), which must come out wrong. |
| Rows | `alloy/isa/softhier.toml`, `alloy/isa/tensix.toml` | The checked instructions each expansion may call. Every row runs on the simulator against a scalar reference, and a planted wrong row must fail (`*_verified.toml`). |

Tile widths differ because the hardware does:
- SoftHier takes 256 lanes, narrowed to the widest power of two that divides every elementwise extent (minimum 16).
- Tensix takes one 32 x 32 tile, 1024 lanes, so an extent that 1024 does not divide is refused, including one shorter
  than a tile (the vectorizer would mask it).

## 2. Where they differ

| | SoftHier v1 | Tensix (eval contract v2) |
|---|---|---|
| Backend entry (under `tilelower.lower`) | `softhiergen.program.generate(sdfg)`, then `write_folder` | `tensixgen.gate.lower(sdfg, scalars)` (a collective, or the front and `tensixgen.split.program(task, sdfg, scalars)`), then `Program.write` |
| Compute | Spatz RVV loops (`dsh_rvv_*`) on core 0 of each cluster; RedMulE for float16 GEMM | SFPU and FPU row calls on DST tiles in one compute kernel |
| Data movement | Copy nodes (iDMA on the DMA core), each followed by its wait (`DmaWait`) and a `Sync` (cluster barrier) | Copy nodes (NoC reads and writes), one `NocWait` after the loads and one around the store, and a `Sync` per circular-buffer handoff (`alloy/tensixgen/movement.py`); the reader and writer kernels spell them. Both follow DaCe's `InsertAsyncWaits`: copies in flight, then the wait before their readers |
| Work split | Cluster `c` runs kernel iterations `c, c + P, ...` | Tiles split evenly over the cores; a reduction sums one partial tile per core on the host |
| Global memory layout | One HBM region, or a placement over HBM nodes (block-cyclic or page-cyclic) | Interleaved DRAM pages, or L1 height shards (one block of the outermost dimension per core) |
| Element types | float32, float16, int32 | float32 |
| Collectives | All nine (`Allreduce` to `Alltoall`, `Barrier`), over iDMA between global barriers | `Bcast`, `Allgather`, `Gather`, `Scatter`, `Alltoall` on whole tiles (`tensixgen/collectives.py`): one dataflow kernel per rank, NoC writes into the receiver's CB and a semaphore count; `Bcast` multicasts. Pipelining and multicast trees are the agent's |
| exp, log | A scalar loop on the Spatz core over the ladder's strict float32 kernel (`dsh_ladder.c`) | The SFPU rows (`exp_tile`, `log_tile`) on ttsim; on the card the SFPI rungs (`rungs.exp`, `rungs.log` in `tensix.toml`), because the card rows miss float32 |
| Waits an agent may move | `alloy_wait_idma` and `alloy_wait_redmule` complete their engine only; the cluster barrier is its own step | `wait on=noc` (reads) and `wait on=noc_write` (writes) complete every transfer issued before them |

## 3. What each refuses

Each entry is an `Unsupported` raised with the reason. Gate rows marked "refused" in
`python -m alloy.tensixgen.gate` name the same reasons.

Both backends refuse:
- masked tiles and masked copies (a remainder tile would need a mask);
- a tile operand that is not one contiguous run.

Only SoftHier refuses:
- control flow around kernels at the top level of the SDFG;
- `/` on int32, a reversed int32 subtraction, and a float16 sum;
- unary ops other than `neg`, `abs`, `sqrt`, `exp`, and `log` (exp and log on float32 only);
- copies with a step inside a row, and copies between two placed arrays;
- a collective or grid barrier in a kernel map of more iterations than clusters.

Only Tensix refuses:
- inputs other than float32;
- more than one output;
- reductions other than a whole sum of one input (so a max reduction is refused);
- tile copies spread over several states (cumsum, the copy chain, GEMM);
- collectives that combine data (`Reduce`, `Allreduce`, `ReduceScatter`), the grid barrier, and collective rows
  that are not whole tiles;
- more live tiles than one DST acquire holds;
- more cores than tiles;
- a placement other than interleaved pages or one height shard per core.

## 4. Known limits

- Spatz `max` and `min` return the other operand when one is NaN (IEEE 754-2019 maximumNumber); NumPy returns NaN.
- GVSoC stops on Spatz mask instructions, so SoftHier compares and selects run as scalar loops on the Spatz core.
- GVSoC stops in newlib's `rintf`, `expf`, and `logf`. The SoftHier ladder rounds with one `fcvt.w.s` instruction,
  and outside the strict kernels' range it computes exp(x) as exp(x/2)^2 and log(x) on x scaled by 2^-64 or 2^64
  (the gate cases "exp beyond the ladder's range" and "log beyond the ladder's range").
- The Tensix SFPU flushes subnormal inputs to zero, so `log_tile` of a subnormal is -inf.
- On the Blackhole card with tt-metal 0.63, `exp_tile` holds bfloat16 accuracy only (max relative error 1.73e-3 on
  [-7, 7]) and `log_tile` missed float32 by 0.0165. The SFPI rungs that replace them were checked on [-7, 7]; the exp
  rung does not clamp, so |x| above about 87 overflows the exponent field.
