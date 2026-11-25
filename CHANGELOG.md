# Changelog

## 0.1.4 (2026-11-25)

- Release candidate: prune and fuse tests, shorten CI, fresh docs (cd85e64)
- Tests, second pass: drop what a bigger test already proves (Tensix kernel-text tests ttsim runs; the 0.6x card spelling stays), reverse cases the exhaustive row tests cover, a CLI duplicate of the lookup refusal, a planted-row structure test its recorded run covers, and best/'s winner check test_api asserts; tag the df65f42 note and mod fixes as reproducers. 2018 -> 2000 cases (f7629e5)
- Tests: per-row gates check a fixed sample (helpers.sample; the verify CLIs check every row), cheap table checks folded into one test each, harness-text tests a planted-bug test already covers dropped, three duplicate refusal tests merged; reproducers carry a '# Reproducer:' line (tests/README.md); mypy: test_mcpserver imports Mode from alloy.report. 4206 -> 2018 cases (1e4c00f)
- Alloy as an MCP server: alloy-mcp (extra mcp) serves alloy_profile, alloy_speculative, alloy_reference, alloy_sweep and alloy_isa over stdio outside the bench; the judge and the server answer alloy_isa through alloy.isa.query (dca51e5)
- SIMT verdicts: the five f64 CUDA rows ran on an A100 (ault25) (4aa2d3d)
- SIMT verdicts: HIP rows ran on an MI50 (gfx906, ROCm 7.2); the five f64 rows (fma, reduce add/min/max, scan add) now run on hardware (94b15a2)
- AMD GPU detection falls back to rocminfo when amdgpu-arch prints nothing (ROCm 7.2 on an MI50); SIMT rows compile for the detected gfx target, not native (290a339)
- Fix CI lint: type the RVV compile flags and the move test's spaces; drop an unused test variable (0379427)
- Tensix tilize and untilize rows (design T5): tilize_block and pack_untilize_block, bit for bit on ttsim in f32 and bf16 against a face-permuting reference; ask inits a layout row once; the alloy-isa plugin skill names rvv (665c350)
- Complexity gate: the loop over a request's elements out of vector_op_1d (spanned) (af1d057)
- ask rvv (T7): RVV answers any length as a vsetvl loop; reductions and scans run their whole program under qemu-riscv64 (tail-undisturbed accumulator, scalar carry) (992b3f2)
- Complexity gate: Tensix op check, move bodies and move references out of answered, body and reference (a628ca6)
- Tensix load, store and transpose rows (T5): CB to DST and back by copy_tile and pack_tile (bit for bit on ttsim, f32 and bf16), transpose_tile per tt-metal version; ask answers CB-DST copies and the transpose op; tensix verify --ops records chosen rows (e488fcd)
- Math kernels fuse every product an addition takes, so each compiler and contraction flag computes the recorded rounding (review R3); records are the worst over gcc, clang, NEON, SVE and RVV, rounded up, and the gate holds them exactly on a prefix of the record's draws; RVV math kernels (293872a)
- f64 device rows (T9): fma, reduce_add/min/max and scan_add in double on CUDA and HIP; the check program runs a row in its own precision on inputs past float's digits (float mutants fail); CUDA rows run on an RTX 4050, HIP compiled for gfx90a and gfx942 (fefa85e)
- Answers over several registers run their whole program (review R12): a CPU reduction or scan hands out the N-element code with its combine, carry and SVE loop, and the check runs it against a scalar reference (planted wrong carries and combines fail); SVE min/max answers include math.h (e20e8a3)
- Tensix reductions (review R12, C14): the largest input sits at row 17, column 4 of the first tile, so a program that reduces only the last tile or a tile's first face fails its ttsim check (it sat in the last element, where those pass) (67389b7)
- SoftHier verdicts rerun on GVSoC after the NumPy NaN max/min fix (alloy 2c7f0de, ault 924422): 35/35 rows, 14/14 planted rows fail, identical to the 11-24 record (21268c6)
- GPU register rows over N elements (T3): lane rows run N / lanes times per lane on coalesced indices, warp reductions fold each lane first then reduce once; N a whole multiple of the warp, else refused with the multiples around it; a multi-warp scan refusal names the carry recipe (2c7f0de)

## Unreleased

- Alloy as an MCP server: `alloy-mcp` (extra `mcp`, module `alloy.mcpserver`) serves `alloy_profile`,
  `alloy_speculative`, `alloy_reference`, `alloy_sweep` and `alloy_isa` over stdio to any MCP client, outside
  HPCAgent-Bench. A program is a `@dace.program` (`file.py:function`) or a saved `.sdfg`; each code-generation call runs
  `api.generate` in a spawned process whose output goes to stderr, never into the protocol stream. The bench's judge
  and the server answer `alloy_isa` through one function (`alloy.isa.query`).
- `ask rvv`: RVV is an `ask` target. A request of any length answers as a `vsetvl` loop (every pass takes vl, the last
  is the tail); reductions and scans hand out and run their whole program under qemu-riscv64.
- Tensix tile moves and transpose (design T5): `copy` between a circular buffer (`shared`) and DST (`tile_register`)
  answers `copy_tile` or `pack_tile`, and `transpose` (a Tensix op) `transpose_tile` (`transpose_wh_tile` on 0.6x);
  all three run on ttsim in f32 and bf16, the moves bit for bit. `python -m alloy.isa.tensix verify --ops ...` runs
  only those rows and keeps the others' records.
- Tensix `tilize` and `untilize` rows (design T5): `tilize_block` turns a row-major 32x32 block in a circular buffer
  into a tile, `pack_untilize_block` a tile into a row-major block; each runs on ttsim in f32 and bf16 bit for bit,
  against a reference that permutes the tile's four faces, so a plain copy fails. `ask tensix tilize` answers one init
  and one call per tile.
- The alloy-isa plugin skill names the `rvv` target.
- Math kernels compute the same rounding under every compiler and flag (review R3): the renderer writes each product an
  addition takes as one fused instruction, within a statement and across them, so `-ffp-contract` and gcc versus clang
  no longer change a kernel's result. Records are the worst over gcc and clang on AVX2 and AVX-512, NEON, SVE and RVV
  under qemu, and every f32 input of the exhaustive kernels, rounded up; the gate holds a kernel to its record exactly
  (it allowed 1.5x) on a prefix of the record's draws. Up to 1.12x on 86 records, lower on 40.
- RVV math kernels: the 180 ladder kernels on RISC-V V 1.0 at LMUL 1 (`kernel rvv ...`), each within its record
  under qemu-riscv64.
- f64 device rows (design T9): `fma`, `reduce_add`, `reduce_min`, `reduce_max` and `scan_add` in double on CUDA and HIP,
  each checked on inputs with digits past float's (a row that rounds through float fails); each ran on hardware (CUDA on an A100, HIP on an MI50, gfx906).
- A CPU reduction or scan over several registers (any length on SVE) hands out the whole N-element program, the
  lane-wise combine, the carry and the `svwhilelt` loop included, and its check runs that program against a scalar
  reference with the extreme in the first, a middle and the last element (review R12); it checked one register only.
  SVE min and max answers name `<math.h>` for their `INFINITY`.
- Tensix reductions: the largest input sits inside the first tile (review R12).
- GPU register rows take N elements over one warp (T3): a lane row (`fma`, ...) runs N / lanes times per lane on
  coalesced indices `i = lane + j * lanes`; a warp reduction folds each lane's values first, then reduces once; N must
  be a whole multiple of the warp (32 on CUDA, 64 on CDNA), else refused with the multiples around it and a bounds-check
  fix. A scan over several warps is refused with the carry recipe (it named the reduction recipe).

## 0.1.3 (2026-11-25)

- Lookup layouts as index maps (dace-relayout >= 0.1.2, a new dependency): an operand's named layout and swizzle
  become relayout operations, and every layout check compares the index maps they give. Two spellings of one map are
  one layout: `b128` on 128-byte rows is `xor:8`, so gfx942 and gfx90a take it (the answer notes the rename), and sm90
  takes `xor:8` there. A 2-D operand may give any layout as relayout operations: `--<name>-layout '<JSON>'` in `ask`,
  `name_layout=<JSON>|@file` in `ask-all`; malformed operations, or ones that are not one-to-one, are Invalid.
- Lookup (owner rulings of 2026-11-25 on the design items): a CPU request with 2-D (or higher) data is answered as
  one run of its elements, row-major or column-major, and the answer says so; mixed layouts, and a scan over
  column-major data, are refused with a transpose fix. Tensix `reduce_add` and `reduce_max` take `dim=row|col|all`
  (`--dim` in `ask`): four new rows (`REDUCE_ROW`, `REDUCE_COL`), each checked on ttsim at f32 and bf16, and a
  planted row that reduces the wrong dimension fails (rel 1.0).
- Wrong results fixed. The Tensix SFPI exp rung saturates (inf above ln FLT_MAX, 0 below the smallest normal) where
  it overflowed the exponent field for |x| above about 87; the card checked it over [-100, 100] (max rel 1.19e-07,
  alloy-tenstorrent agents `8ec7b7d`), so its bound is 2.0 ulp. SoftHier's `max` and `min` (elementwise, with a
  scalar, and the reductions) return NaN for a NaN operand as NumPy does; Spatz's `vfmax` and `vfmin` returned the
  other operand. A NaN input reaches a SoftHier program as the quiet NaN (it was refused), and the gate's check
  (`alloy.gate.error`) takes NaN and inf as exact matches. Two gate cases: a max reduction over a NaN, and maximum
  and minimum with NaN.
- Tensix max reduction: the tiles fold with the SFPU `max` row, and the ttsim host takes the max of the partial
  tiles. The card's contract v2 host sums the partial tiles, so the card spelling refuses it.
- Tensix several outputs (ttsim): output k leaves through CB 16 + k, and the writer stores every output before one
  barrier. Whole rows as a tile: when every array's rows are K < 1024 elements, the tile is 1024 / K rows (still 1024
  consecutive elements). Gate case: two outputs over 8 x 256 rows. The CloudSC nests stay refused on Tensix:
  saturation needs more live tiles than one DST acquire holds, and liq_ice_frac and init are several tile bodies.
- One entry point to both tile backends: `alloy.tilelower.lower(sdfg, "softhier" | "tensix")` returns the generated
  sources; Tensix reads its task (inputs, output, map or reduce) off the SDFG. Both gates lower through it, and every
  gate program is byte-identical to before. The shared front refuses an extent shorter than the tile, which the
  vectorizer let through as one masked tile (Tensix then failed on `TileMaskGen`).

## 0.1.2 (2026-11-25)

- RISC-V V 1.0 joins the lookup as `rvv`: 86 rows over f64, f32, i64, and i32 (LMUL 1, `__riscv_` v1.0 spellings),
  the strip-mined `rvv_vsetvl` schedule with its skeleton, and llvm-mca costs on SiFive X280. Every row except the
  transcendentals runs under qemu-riscv64 at VLEN 256 against the scalar reference, as SVE runs under qemu-aarch64.
- `reverse` takes dotted RVV mnemonics (`vfmacc.vv`).
- SoftHier: Spatz rows for sub, div, min, max, neg, abs, sqrt, and reduce_min, checked on GVSoC with a planted wrong
  row each. softhiergen lowers `numpy.where` and comparisons (a compare into a bool tile, then a select, with a tile
  or a scalar arm; both scalar loops on the Spatz core, because GVSoC's Spatz model stops on mask instructions),
  `numpy.cumsum` (each cluster scans its share, then adds the allgathered totals of the clusters before it), and
  lengths 256 does not divide (the widest power-of-two tile that divides them, down to 16). int32 tiles pass the Spatz
  loops by cast (rv32 newlib's `int32_t` is `long`), and the image's compilers write temporaries in the bound folder
  (`verify --image` failed under a host `TMPDIR`).
- SoftHier waits complete their engine only (`alloy_wait_idma`, `alloy_wait_redmule`); the cluster barrier that lets
  other cores read is its own step (`barrier kind=cluster`), so an agent can overlap. The iDMA rows state the 16
  transfers in flight and that the wait completes all of them (no handle per transfer).
- `ask tensix copy`: whole float32 tiles between DRAM and a core's circular buffer, in tensixgen's reader and writer
  spelling, completed by `wait on=noc` (reads) or the new `wait on=noc_write` (writes).
- One gate for both tile backends (`alloy.gate`): the same NumPy cases, one check per element
  (`|out - ref| <= tol (|ref| + max |ref|)`, integers and bools exact) and a planted wrong program each. tensixgen
  runs the cases on ttsim (`python -m alloy.tensixgen.gate run`; the host takes a case's own inputs) and reports the
  cases it refuses; both backends share the front that fuses maps and vectorizes (`alloy.tilelower`). A Tensix sum
  reduction is recognized in any spelling of `a + b`.
- Tensix: compare rows (`lt`, `gt`, `le`, `ge`) and `select` (`where_tile`, float32), verified on ttsim; tensixgen
  lowers `numpy.where` and comparisons (bool tiles stay transient, a scalar arm becomes a filled tile), and the shared
  front simplifies the SDFG before fusing.
- Tests: dropped the profile-tool packet grade (14 min in CI); one speculative packet run checks the answer, the
  episode folder, and the grade; the speculative flavor runs on atax only; the intrinsic-tasklet smoke drops
  tsvc_2_vpv; one DaCe-backend test covers the build, its reuse, and a changed program (two sweeps for four).
- SoftHier: `numpy.exp` and `numpy.log` on float32 tiles lower to scalar loops on the Spatz core over the ladder's
  strict kernels (`dsh_ladder.c`, which the program folder carries; the link adds newlib's libm for the strict
  kernels' out-of-range path; rounding is one `fcvt.w.s` because newlib's `rintf` stops GVSoC). The gate gains
  softplus (correct on GVSoC, rel 3.2e-08).
- Tile backends share one front (`alloy.tilelower.front`: fuse, then vectorize) and one refusal class
  (`alloy.tilelower.Unsupported`, the base of softhiergen's `LoweringError` and tensixgen's `Refused`); a length the
  tile does not divide is refused alike on both. The front's simplify skips dead-dataflow elimination, which dropped
  the copy that fills a rooted collective's output (the gate's gather and reduce came out wrong).
- `docs/tile-backends.md` sets softhiergen and tensixgen side by side: the shared front and gate, the differences,
  what each refuses, and the known limits; `docs/softhiergen.md` follows the code again (front, compares, exp and log).
- CloudSC in the gate: float32 transcriptions of the saturation, liquid/ice fraction and init nests, on the bench
  initializer's draws against the bench's float64 NumPy reference (`alloy/softhiergen/gate/cloudsc.py`). Both gates
  read one case list (`programs.all_cases`). A specialized SDFG lowers on both backends (the front substitutes the
  specialized sizes, so the vectorizer leaves no size guard and SoftHier's tile width reads them); `numpy.full` (a
  constant TileGather) is a fill on both (Spatz `dsh_rvv_fill_*`, Tensix `fill_tile`). Tensix refuses the CloudSC
  nests: each writes several outputs, and contract v2 writes one.
- Tensix default collectives (`alloy/tensixgen/collectives.py`): `Bcast`, `Allgather`, `Gather`, `Scatter`, and
  `Alltoall` of the gate's in-kernel form, one dataflow kernel per rank that writes whole tiles over the NoC into the
  receiver's circular buffer and counts arrivals on a semaphore; `Bcast` multicasts. All five run correct on ttsim.
  Collectives that combine data are refused (they need the compute kernel). The gate's collective cases move one
  1024-float block per rank (was 256), one Tensix tile, so both backends run the same cases.
- Tensix data movement is copy, wait and sync nodes in the tile body (`alloy/tensixgen/movement.py`), the model of
  softhiergen and of DaCe's `InsertAsyncWaits`: the loads are copies in flight before one `NocWait`, a `Sync` per
  circular-buffer handoff, the store between a `Sync` and its `NocWait`. The reader and writer kernels are spelled
  from these nodes, and so are the default collectives' row load and store (their NoC writes between ranks stay the
  collective's own); every generated program is byte-identical to before.
- SoftHier: newlib's `expf` and `logf`, which the strict ladder kernels called outside their range, stop GVSoC like
  `rintf`; the ladder unit computes those values itself (exp(x/2)^2, log on x scaled by 2^-64 or 2^64). Two gate
  cases feed exp and log values beyond the kernels' range; both backends compute them correctly.
- CI: the Tensix rows run at their own dtypes (`tensix.row_dtypes`: select is float32 only); mypy and pyright clean.
- HPCAgent-Bench comes from its PyPI release (1.0.0), no longer from a git commit; `helpers/release_patch.sh`
  drops a git source of one of our packages instead of moving it to a tag, so pins name released versions.

## 0.1.1 (2026-11-24)

A fix to profile mode: a timing draw that crashed the reference program no longer loses the episode.

- Size presets carry the manifest's first `config` row (`K`): a kernel whose input initializer reads a config entry
  raised `KeyError: 'K'` at every timing draw (`ext_break_capture`, `fuse_move_ifs`, `versioned_distance_update`).
- The verifying child tells distinct outputs apart by a BLAKE2b digest read in place, not a joined byte copy of every
  output, which ran it out of its memory share at large sizes (`MemoryError`).
- When Alloy's timer raises, profile mode delivers the plain program and keeps the episode record, as it does when
  its pick grades slower. Before, the episode exited without a submission.

## 0.1.0 (2026-11-23)

The first release, published on PyPI as `dace-alloy`. The import name is `alloy`.

    pip install dace-alloy

Alloy runs on DaCe extended, published on PyPI as `dace-extended` (import name `dace`), which pip installs with it; a
checkout of https://github.com/ThrudPrimrose/dace-alloy installs the same release with `uv sync --extra dev`.

What it contains:

- Per-scope speculative code generation for DaCe programs (`alloy.api.generate`): Alloy outlines a program into
  scopes, renders each scope under the codegen knobs, compilers and FP levels of `configuration_matrix.toml`,
  verifies every candidate on fuzzed inputs, times the survivors, and links the best per scope into one program with
  a report (`report.json`, `report.md`).
- DaCe's build plugin `alloy-speculative`: set `compiler.build_plugin = alloy-speculative` and `sdfg.compile()` runs
  the per-scope selection; an SDFG with GPU device maps gets threadblock speculation (`alloy.gpu`).
- The machine-abstract math ISA (`python -m alloy.isa`): checked rows for AVX2, AVX-512, NEON, SVE and SME, CUDA and
  HIP device rows, sm90 and CDNA tile kernels, Tenstorrent Tensix and SoftHier rows, `llvm-mca` costs, and the `ask`
  and `ask-all` lookups an agent queries for a target's spelling of an operation.
- Code generation for Tenstorrent Tensix (`alloy.tensixgen`) and SoftHier v1 on GVSoC (`alloy.softhiergen`).
- The C front end (`alloy.frontend.cnumpy`): a C kernel plus a binding JSON to canonical NumPy and its SDFG.
- The HPCAgent-Bench plugin (`alloy.hb_plugin`, entry point `hpcagent_bench.plugins`), with its skills, prompts and
  tools.

Extras: `bench` (HPCAgent-Bench, for manifest inputs and the tolerance band), `nvgpu` and `amdgpu` (cupy), `softhier`
(the GVSoC launcher's Python packages), and `dev` for tests.
