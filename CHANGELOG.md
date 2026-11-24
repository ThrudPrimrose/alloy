# Changelog

## Unreleased

- RISC-V V 1.0 joins the lookup as `rvv`: 86 rows over f64, f32, i64, and i32 (LMUL 1, `__riscv_` v1.0 spellings),
  the strip-mined `rvv_vsetvl` schedule with its skeleton, and llvm-mca costs on SiFive X280. Every row except the
  transcendentals runs under qemu-riscv64 at VLEN 256 against the scalar reference, as SVE runs under qemu-aarch64.
- `reverse` takes dotted RVV mnemonics (`vfmacc.vv`).
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
