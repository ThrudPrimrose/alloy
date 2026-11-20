# softhiergen design

Status: the code as built, 2026-11-19. This file describes what `alloy.softhiergen` does today. The owner's
decisions of 2026-11-19 (DaCe's tile nodes and vectorizer, DaCe's sync and communication nodes, no TCDM
planner) replaced the 2026-11-10 design. The code moved into Alloy from `ThrudPrimrose/dace-softhier` (main
57d9d43), whose `docs/HANDOFF.md` and `docs/items/` keep the history of that earlier plan.

## 1. Goal

softhiergen generates code for the SoftHier v1 many-cluster RISC-V accelerator from DaCe SDFGs. It is a
plugin: importing `alloy.softhiergen` registers two storages, a schedule, a code generation target and SoftHier
expansions of DaCe's copy, tile, sync and communication nodes. DaCe itself is never edited. Removing the
package removes SoftHier support.

`alloy.softhiergen.program.generate(sdfg)` lowers a NumPy program's SDFG (all symbols specialized) in place and
returns one C++ unit; `write_folder` adds the data unit and a build-and-run script for GVSoC;
`read_results` parses the arrays the run printed.

## 2. Pinned sources

DaCe is Alloy's pin (`[tool.uv] override-dependencies` in `pyproject.toml`). The simulator, the SDK and the
toolchain are the SoftHier v1 stack of `alloy/isa/softhier_pins.toml` (GVSoC with the gvsoc-pulp model
`pulp/chips/soft_hier_old` at `6a00247dc3`, the softhier-sdk at `c32f3eba21`, GCC 14.2.0); the gate runs in the
image `helpers/build_softhier_image.sh` builds from it.

Facts about the toolchain archive (listed, not yet unpacked): it contains `riscv32-unknown-elf-gcc`,
`riscv32-unknown-elf-g++`, libstdc++ headers (`include/c++/14.2.0`) and `riscv_vector.h`. The second
archive the SDK downloads (`pulp-riscv-gnu-toolchain` v1.0.16) is an older GCC; softhiergen uses only
the GCC 14 one.

## 3. Platform

### 3.1 SoftHier v1 (target of this work)

GVSoC target `pulp.chips.soft_hier_old.flex_cluster`, launched with the legacy `gvsoc` launcher.

Structure (facts, from `flex_cluster.py`, `flex_cluster_arch.py`, the SDK headers):

- A 2D mesh of `num_cluster_x * num_cluster_y` clusters. Cluster id `cid = y * num_cluster_x + x`.
- Each cluster has `num_core_per_cluster` Snitch cores, a TCDM (SRAM, `cluster_tcdm_size` bytes, at local
  address `cluster_tcdm_base`), an iDMA engine, a RedMulE matrix accelerator, optional Spatz vector units
  on the cores listed in `spatz_attaced_core_list`, an instruction memory at `0x80000000` and a stack
  memory at `0x10000000`.
- All cores of all clusters execute the same ELF from `_start`. The linker script (`flex_memory.ld`) places
  `.text`, `.rodata`, `.sdata`, `.sbss` and `.bss` in region `L3` at `0x80000000`, the instruction memory of each
  cluster (`instruction_mem_size` bytes), so zero-initialized statics are shared by the cores of one cluster and
  private between clusters. `.data` and `.hbm` go to region `HBM` at `0xC0000000` (side HBM, one copy for all
  clusters); `.l1` goes to region `L1` from `0x10`, the TCDM. The regions are larger than the memories, so the
  linker does not catch an overflow.
- Remote TCDM: cluster `cid`'s TCDM is visible to every cluster at
  `cluster_tcdm_remote + cid * cluster_tcdm_size + offset` (`remote_cid`, `remote_xy`).
- Side HBM: channels on the four mesh edges, `hbm_chan_placement = [west, north, east, south]`. Address
  of edge node `nid` (SDK macros):
  - `hbm_west(nid, off)  = HBM_BASE + nid * NODE_SPACE + off`
  - `hbm_north(nid, off) = HBM_BASE + (nid + NY) * NODE_SPACE + off`
  - `hbm_east(nid, off)  = HBM_BASE + (nid + NY + NX) * NODE_SPACE + off`
  - `hbm_south(nid, off) = HBM_BASE + (nid + 2 * NY + NX) * NODE_SPACE + off`
  with `HBM_BASE = hbm_start_base` (default `0xC0000000`) and `NODE_SPACE = hbm_node_addr_space`.
  `arch.node_bases()` lists the nodes in this order; the v1 configuration (`hbm_chan_placement = [2, 0, 0, 2]`)
  has west0 `0xC0000000`, west1 `0xC4000000`, south0 `0xD8000000` and south1 `0xDC000000`. The probe
  `gate/hbm_probe.py` (ault job 920009) showed that GVSoC preloads each of them from its own ELF section and load
  segment and that every cluster's iDMA reads and writes each of them.
  Addresses are 64-bit; the DMA calls take `uint64_t`.
- Stacked DRAM (`dram3d_enable = 1`): one DRAMSys instance above each cluster, at
  `dram3d_addr_base + cid * dram3d_node_space + offset` (default base `0x10000000000`).
- iDMA calls (SDK `flex_dma_pattern.h`): `flex_dma_async_1d(dst, src, bytes)`,
  `flex_dma_async_2d(dst, src, bytes, dst_stride, src_stride, repeat)`, `flex_dma_async_wait_all()`,
  `flex_dma_async_broadcast(dst_off, src_off, bytes, row_mask, col_mask)`,
  `flex_dma_async_reduction(dst_off, src_off, bytes, fmt, row_mask, col_mask)` with formats
  `COLLECTIVE_RED{ADD,MAX}_{UINT,INT,FP}_16`.
- RedMulE (SDK `flex_redmule.h`): `flex_redmule_config(m, n, k)`,
  `flex_redmule_trigger(x_off, w_off, y_off, format)`, `flex_redmule_wait()`. Formats:
  `REDMULE_{NONE,UINT,INT,FP}_16`, `REDMULE_{UINT,INT,FP}_8`. The three addresses are TCDM offsets. In the
  SDK example the accumulator `Y` is loaded before the trigger and holds the result afterwards.
- Spatz stores complete after the core has issued them (gvsoc-core `Ara::insn_end` writes the data when the VLSU
  finishes). `fence` does not wait for them on the model (`fence_exec` checks the scalar LSU only), and neither do
  the barriers (`csrr 0x7C2`); a scalar load or store of the Spatz core stalls until they have ended
  (`Sequencer::load_store_handler`). The model's RVV has no widening reduction (`vfwredusum`) and no `vfrdiv.vf`
  (`isa_rvv_timed.py`): `s - x` and `s / x` broadcast `s` (`vfmv.v.f`) and take the vector-vector op.
- Synchronization: `flex_intra_cluster_sync()` (barrier over the cores of one cluster),
  `flex_barrier_xy_init()` once and `flex_global_barrier_xy()` (barrier over all clusters).
- Roles (SDK convention, used in every SDK example): the last core of a cluster (`flex_is_dm_core()`)
  issues DMA; the first core (`flex_is_first_core()`) drives RedMulE.
- Program frame (SDK `app_example/main.c`): `flex_barrier_xy_init(); flex_global_barrier_xy();`
  timer start on core 0 of cluster 0, body, barrier, timer end, barrier, `flex_eoc(status)`.
- Region-of-interest timing: `flex_timer_start()` / `flex_timer_end()`; the simulator prints
  `[Performance Counter]: Execution period is <n> ns`.
- Preload: `gvsoc ... --preload <elf> --preload-mode direct|timed`; every `PT_LOAD` segment of the ELF is
  written to its physical address. `direct` costs no simulated time and is the default on the pinned
  branch. ELF64 is accepted for addresses above 4 GiB.
- Dump: `flex_dump_open()`, `flex_dump_hbm(offset, bytes)`, `flex_dump_close()` make the simulator write
  a text file with a line `HBM offset == .0x<16 hex digits>:` followed by one `  0x%04x` line per 16-bit
  word.

Unverified:

- Whether a cluster may be configured with one core, and which core may trigger RedMulE.
- Stack size per core. A related project reports that its SDK version spaced core stacks 1 KB apart
  (`runwangdl/softhier-mlir`, `docs/SIMULATOR_NOTES.md`, item 11). Generated code must assume small
  stacks until measured.
- That the Spatz model executes every RVV instruction GCC 14 emits for the intrinsics we use.
- That iDMA accepts local TCDM as both source and destination.
- The exact semantics of the collective row and column masks.
- That the GVSoC control proxy can read and write TCDM and HBM on this target.

### 3.2 softhier_v2 (deferred)

`pulp/chips/softhier_v2` on gvsoc-pulp master is a different platform: clusters with Spatz, TCDM and
iDMA v3 on a FlooNoC with eight selectable topologies, launched with `gvrun`. It has no HBM, no stacked
DRAM, no RedMulE, no collectives and no preload. It is not targeted.


## 4. Package layout

```
alloy/softhiergen/
  __init__.py          imports the modules below, which register everything
  arch.py              Arch: the v1 configuration (field names of the simulator's FlexClusterArch), V1, node_bases()
  storage.py           SoftHier_TCDM, SoftHier_HBM, SoftHier_Device
  hbm.py               array placement over the HBM nodes: checks, sections, share names, element positions
  passes.py            lower(): the lowering pipeline (section 6)
  program.py           generate(), write_folder(), read_results()
  codegen/target.py    SoftHierCodeGen
  library/
    common.py          core roles, operand checks, LoweringError
    kernels.py         whole-array nodes as kernels (SoftHierKernel)
    dma.py             copy nodes as iDMA transfers (SoftHierDMA)
    rvv.py             tile nodes on Spatz (SoftHierRVV)
    redmule.py         TileMMA on RedMulE (SoftHierRedMulE)
    collectives.py     DaCe's communication nodes over the clusters (SoftHier)
    sync.py            Sync, DmaWait, RedmuleWait (SoftHier)
  runtime/include/softhiergen/
    dsh.h              what the generated C++ unit includes instead of <dace/dace.h>
    dsh_math.h         py_floor and py_mod (Python's // and %), which placement addresses use
    dsh_rt.h, dsh_rt.c the runtime over the SDK (C): roles, barriers, iDMA, RedMulE, collectives
    dsh_rvv.h          strip-mined RVV loops over riscv_vector.h
  gate/                the simulator gate: NumPy programs, prepare and check, ault.sh
tests/test_softhiergen_*.py  tests without the toolchain; the `softhier` marker needs the RISC-V GCC
```

## 5. Program model

- **Kernel.** A top-level map with schedule `SoftHier_Device`. Every core of every cluster runs the
  generated `__dsh_program`, which calls the kernels in program order with a global barrier between them.
  Cluster `c` runs iterations `c, c + P, ...` of the kernel map flattened row-major (`P` =
  `V1.num_clusters`); each map parameter is recovered from the flat index with `/` and `%`.
- **Top level.** Outside kernels, the SDFG holds only access nodes and kernels, in a straight sequence of
  states. Control flow around kernels is a `LoweringError`; it belongs inside a kernel.
- **Storages.** `SoftHier_HBM`: every global array. The linker places it in `.hbm` (side HBM, west channel
  0), which the simulator preloads. An array with a `placement` (`dace.placement.Placement`, block-cyclic per
  dimension or page-cyclic) is one share per node instead: node `k` of the placement is HBM node `k` of
  `node_bases()`, its share the C array `__dsh_<name>_node<k>` in section `.hbm` (`k = 0`, after `.data`) or
  `.dsh_hbm<k>` (at the node's base), holding element `idx` at element `offset_of(idx)` of share
  `node_of(idx)`. Every share has the size of the largest one (`local_shape`), padded to 64 bytes.
  The table `__dsh_<name>_nodes` lists the shares, so an element's address is the share's base plus
  `offset_of(idx) * itemsize`. `SoftHier_TCDM`: every transient array inside a kernel, a static in
  `.l1` at one address on every cluster, placed by the linker (no planner). A transient scalar inside a
  kernel is `Register`: every core computes it.
- **Roles.** Control flow and scalar tasklets run replicated on every core. Library node expansions guard
  their effect by role: the compute core (core 0, `dsh_is_compute_core()`) drives Spatz and RedMulE; the
  DMA core (the last core, `dsh_is_dma_core()`) issues iDMA.
- **Sync rule.** After each role-guarded node (iDMA, RedMulE, Spatz), `insert_sync` places the wait for
  its engine (`DmaWait`, `RedmuleWait`; for Spatz the tasklet itself ends with `dsh_vfence()`, a `fence` and a
  scalar load) and then a cluster barrier
  (`Sync`, scope `BLOCK`), ordered by empty edges before every reader of the node's outputs. A copy with
  `sync = False` gets neither: the pass that cleared it places them. Collectives synchronize themselves
  with global barriers. A user's `Sync` node expands to `dsh_cluster_sync()` (`BLOCK`) or
  `dsh_global_barrier()` (`GRID`); other scopes are a `LoweringError`. A `GRID` sync, like a collective, needs a
  kernel map of one iteration per cluster.
- **Vector code.** Every vector instruction lies in a `dsh_rvv_*` function (`noinline`), which only the compute
  core calls; inlined into a guarded caller, GCC could hoist `vsetvl` or a load above the guard onto a core without
  Spatz.

## 6. Lowering: `passes.lower(sdfg, tile=256)`

1. `MapFusionVertical`, `RedundantArray` and `RedundantSecondArray` (an in-place update such as
   `y[:] = a * x + y` then writes `y` directly; after vectorizing, DaCe cannot prove the tile body elementwise),
   then DaCe's vectorizer (`VectorizeCPUMultiDim`, widths `(tile,)`, `ISA.SCALAR`, `assume_even`, fused
   multiply-add) turns elementwise maps into tile maps of tile nodes. An extent that `tile` does not divide is a
   `LoweringError` (the remainder tile would need a mask).
2. Every global array goes to `SoftHier_HBM`. An array with a placement must pass `placement.check(shape,
   hbm_node_addr_space // itemsize, constants)` (every element its own node and offset, node ids exactly
   `0 .. nodes - 1`, each share fits one node), and `nodes` must not exceed the model's HBM nodes; otherwise
   `LoweringError`.
3. `expand_whole_array_nodes`: an access-to-access edge becomes a `CopyLibraryNode` with the edge's
   subsets (a library node's transient output that only relays into another array is written there
   directly). Each top-level library node (matrix product, reduction, copy, allreduce) expands with
   `SoftHierKernel` to a nested SDFG holding one kernel over the clusters, and the nested SDFGs are inlined.
4. Each remaining top-level map becomes a `SoftHier_Device` kernel; its transients go to TCDM (arrays) or
   registers (scalars).
5. `check_top_level` enforces the top-level rule of section 5; `check_placed_access` refuses any node in a kernel
   other than a copy that reads or writes a placed array (only the iDMA expansion computes its addresses).
6. `select_implementations` gives every library node inside a kernel its SoftHier implementation
   (`KERNEL_IMPLEMENTATIONS`); a node without one is a `LoweringError`. A communication node or a `GRID` sync
   needs a kernel map of exactly one iteration per cluster, since both meet in global barriers.
7. `insert_sync` applies the sync rule.
8. `sdfg.expand_library_nodes(recursive=True)`.

Every expansion checks its operands and raises `LoweringError` with the reason; no node falls back to an
element-wise loop.

## 7. Library nodes

- **Whole-array kernels** (`kernels.py`). Each splits the leading dimension evenly over the clusters (it
  must divide) and moves its share HBM to TCDM and back with iDMA copy nodes. Operands must be whole
  arrays. `MatMul` and `Gemm` (`alpha = 1`, `beta = 0`, no transposes): a block of rows of A and C and all
  of B per cluster, one `TileMMA` on RedMulE. `Reduce` of a whole vector with `+`, `max` or `min`: a Spatz
  reduction of each share, then an `Allreduce`. `CopyLibraryNode` between two whole arrays: staged through
  TCDM. `Allreduce`: row `c` is cluster `c`'s buffer.
- **Copies** (`dma.py`, `SoftHierDMA`). Each side must be one contiguous run or a stack of equal
  contiguous rows; both sides move the same element count and dtype. A step of the outer range multiplies the
  row stride (`X[0:16:2, 0:10]`); a step inside the row is refused. A 1D copy is `dsh_dma_1d`, a 2D one
  `dsh_dma_2d` with both strides. A masked copy is refused. `MaskedCopyLibraryNode` is a
  `CopyLibraryNode` and takes the same implementation. One side of a copy may be a placed array (both placed is
  refused). When every distributed dimension's range provably lies in one block (step 1, the block a multiple of
  the extent, and the start a multiple of the extent for every value of the enclosing map parameters), the copy
  stays on node `node_of(start)` and is a box of that node's share: one 1D or 2D transfer from the share's base
  plus `offset_of(start)`. Otherwise the DMA core loops over the rows of the placed side and cuts each row where a
  block of the last dimension ends, one `dsh_dma_1d` per run, with node and offset computed per run; the other side
  must then be one run or rows of the placed side's row length.
- **Tile nodes on Spatz** (`rvv.py`, `SoftHierRVV`). `TileBinop` (`+ - * / min max`, tile-tile and
  tile-scalar forms, the reversed loop for scalar `-` or `/` tile), `TileUnop` (`neg`, `abs`, `sqrt`),
  `TileFMA`, `TileReduce` of a whole tile (`+`, `max`, `min`). Element types `float32`, `float16`, `int32`; no
  `/` on `int32`, no reversed `int32` subtraction, and no `float16` sum (the model has no widening reduction, and
  a `float16` accumulator loses the sum). Tile operands must be contiguous TCDM runs; masks are refused.
- **TileMMA on RedMulE** (`redmule.py`, `SoftHierRedMulE`). `float16`, `alpha = 1`, `beta` 0 or 1, all
  operands contiguous TCDM runs; `_cin` must be `_c`'s container and subset, because RedMulE accumulates in
  place. `beta = 0` zeroes `c` with Spatz first and fences the fill. Emits `dsh_redmule_mma(a, b, c, m, k, n)`,
  which loads the RedMulE registers and issues config and trigger in one asm statement.
- **Collectives** (`collectives.py`). `Allreduce`, `Reduce`, `ReduceScatter`, `Bcast`, `Allgather`,
  `Gather`, `Scatter`, `Alltoall` and `Barrier`; ranks are clusters, buffers contiguous TCDM runs. Each
  is one runtime call: iDMA pushes into the peers' TCDM between global barriers, the compute core combining
  reduction slots in rank order. Reductions take `float32`, `float16` or `int32` with sum, prod, max or
  min, but no `float16` sum. Buffer sizes must match the collective (`COUNTS`: e.g. an allgather output is `P`
  times its input). Only `Allreduce`, `Reduce`, `ReduceScatter` and `Bcast` may have input and output in one
  container: each reads its input before any cluster writes an output. In the others a peer's push can overwrite
  an input before it is sent. `Barrier` is `dsh_global_barrier()`.

## 8. Code generation

`SoftHierCodeGen` (target `softhier`) emits each kernel as a function of one C++ unit whose body DaCe's
CPU generator produces. It defines TCDM arrays as `.l1` statics and transient HBM arrays as `.hbm`
objects (a placed one as its shares), declares global arrays, the shares of placed ones, and scalar arguments
`extern "C"` (the data unit defines them), emits each placed array's table of shares, prints SDFG
constants as `constexpr` with `sym2cpp`, and refuses any access-to-access copy left after lowering. The
frame code DaCe always generates is not used: `generate` returns only the SoftHier code object.

The program folder (`write_folder`) holds `kernels.cpp`; `main.c`, which bakes the inputs into `.hbm`
arrays of their element type (exact hex float literals; a NaN input is refused), checks `ARCH_NUM_CLUSTER` against `V1.num_clusters` at compile time, runs the SDK frame
around `__dsh_program` with a cycle count, and prints every array through a TCDM buffer; `arch.py` for
`SOFTHIER_ARCH_FILE`; the runtime headers; `meta.json`; and `build_run.sh`, which compiles with the SDK's
flags without `-ffast-math`, links with its start code and linker script, fails when the sections linked to `L3`
pass `instruction_mem_size` or `.l1` passes `cluster_tcdm_size - 0x10`, and runs GVSoC. `write_folder` refuses a
program whose HBM arrays without placement pass the west channels (`hbm_chan_placement[0] * hbm_node_addr_space`
bytes). A placed array's inputs are scattered into its shares by `node_of` and `offset_of`, each share dumped in
node order; `meta.json` keeps every element's position in the shares (`node * share + offset`), and
`read_results` gathers the array back from them. With placed arrays over more than one node, `build_run.sh`
links with `link.ld`: the SDK's `flex_memory.ld` plus one `PT_LOAD` segment and one section `.dsh_hbm<k>` at
the node's base for each node after the first, and `write_folder` refuses a program whose arrays pass
`hbm_node_addr_space` on any node (node 0 also holds `.data` and the arrays without placement). A program without
placed arrays gets the same `kernels.cpp`, `main.c`, `meta.json` and `build_run.sh` as before placement existed.
`read_results` reads the printed words back into arrays.

Limitation: `max` and `min` on Spatz (`vfmax`, `vfmin`, `vfredmax`, `vfredmin`) return the other operand when one
is NaN (IEEE 754-2019 maximumNumber); NumPy returns NaN.

## 9. Shortcuts in the code

Each is marked `shortcut:` where it lives.

- Inputs are baked into the ELF; new data means a relink (`program.py`).
- One cluster barrier per role-guarded node, also where a later one would cover it (`passes.py`).
- Whole-array kernels split the leading dimension evenly and hold one share in TCDM at once (`kernels.py`).
- All-to-all patterns run as `P` turns of one sender each; all senders at once hangs the v1 model
  (`collectives.py`).
- A copy that crosses a block of a placed array is one 1D transfer per run, issued in a loop (`dma.py`).

## 10. Testing

`tests/` runs without the toolchain (`pytest -m "not softhier"`): generated-code strings, the SDFG after
single passes, and the `LoweringError` of each refused case. `tests/test_softhiergen_placement.py` compiles the iDMA
code of copies to and from placed arrays with the host `g++` (transfers as `memcpy`) and compares the moved elements
with NumPy; it skips without a host `g++`. The `softhier` marker builds a program with
the RISC-V GCC and checks that no vector instruction lies outside a `dsh_rvv_*` function. The gate (`alloy/softhiergen/gate/`) compares simulator results with NumPy on ault:
`python -m alloy.softhiergen.gate.run prepare <dir>`, `alloy/softhiergen/gate/ault.sh <dir> <name>`, `python -m alloy.softhiergen.gate.run check <dir>`.
