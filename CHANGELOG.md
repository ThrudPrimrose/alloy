# Changelog

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
