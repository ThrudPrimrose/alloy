# Alloy

Speculative per-region code generation backend for DaCe. Input: a dace numpy program with symbolic sizes.
Alloy splits it into regions, renders each region under many codegen knobs, compilers and FP levels,
verifies every candidate, times the survivors, and links the best into one program plus a per-region report.

    uv sync --extra dev
    alloy build examples/two_regions.py:two_regions --out out/   # regions, candidates, verdicts, report.md

Inputs come from an HPCAgent-Bench style manifest next to the program (`two_regions.yaml`: sizes, a `fuzzed` range,
init arrays, input and output args); without one, candidates are built but not verified.

Layout:

- `alloy/`: the package. `regions` outlines a program, `candidates` enumerates the sweep, `build` renders, compiles and
  checks one candidate, `runtime` resolves and checks the OpenMP runtime, `sweep` runs it all, `report` writes the
  result, `cli` is `alloy build`. Every compiler, flag and option is in `alloy/configuration_matrix.toml`.
- `examples/`: input programs for Alloy (dace numpy with symbolic sizes).
- `samples/`: A/B studies. Each holds a slow and a fast rendering of one kernel, the harness, and the setup that
  measured the gap.
- `tests/`: one file per module, plus the cross-compiler OpenMP link test.
- `docs/`: design decisions with build status, measurement rules, related work.

Tests: `pytest -m "not icx"` on a box without Intel oneAPI (each compiler is a pytest mark); CI installs gcc,
clang, oneAPI and the NVIDIA HPC SDK and runs everything, including the cross-compiler OpenMP link test.

Notes: `docs/design.md` (decisions), `docs/measurement.md` (A/B rules), `docs/related_work.md` (citations).
