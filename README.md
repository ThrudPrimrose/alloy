# Alloy

Speculative per-region code generation backend for DaCe. Input: a dace numpy program with symbolic sizes.
Alloy splits it into regions, renders each region under many codegen knobs, compilers and FP levels,
verifies every candidate, times the survivors, and links the best into one program plus a per-region report.

    uv sync --extra dev
    alloy build examples/two_regions.py:two_regions --out out/   # regions, candidates, report.md

`samples/` holds A/B pairs: a slow and a fast rendering of one kernel, with the setup that measured the gap.

Tests: `pytest -m "not icx"` on a box without Intel oneAPI (each compiler is a pytest mark); CI installs gcc,
clang, oneAPI and the NVIDIA HPC SDK and runs everything, including the cross-compiler OpenMP link test.

Notes: `docs/design.md` (decisions), `docs/measurement.md` (A/B rules), `docs/related_work.md` (citations).
