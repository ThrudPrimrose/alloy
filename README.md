# Alloy

Speculative per-scope code generation backend for DaCe. Input: a dace numpy program with symbolic sizes.
Alloy splits it into scopes, renders each scope under many codegen knobs, compilers and FP levels,
verifies every candidate, times the survivors, and links the best into one program plus a per-scope report.

    uv sync --extra dev

```python
import pathlib
from alloy import api
from alloy.frontend import inputs
from examples.two_scopes import two_scopes

manifest = inputs.load(pathlib.Path("examples/two_scopes.yaml"), "examples/two_scopes.py:two_scopes")
result = api.generate(two_scopes.to_sdfg(), pathlib.Path("out"), manifest=manifest)  # result.report: report.md
```

Extras: the core (outline, sweep, build) needs only DaCe. `bench` adds HPCAgent-Bench, which verification and
timing use for manifest inputs and the tolerance band. `nvgpu` / `amdgpu` add the matching cupy build. `dev` is
`bench` plus the test tools (CPU, what CI installs); `dev-nvidia` and `dev-amd` add the GPU extra.

Inputs come from an HPCAgent-Bench style manifest next to the program (`two_scopes.yaml`: sizes, a `fuzzed` range,
an `args` block); without one, candidates are built but not verified.

Layout:

- `alloy/frontend/`: `scopes` outlines a program, `inputs` draws its inputs from a bench manifest.
- `alloy/backend/`: `candidates` enumerates the sweep, `build` renders, compiles and checks one candidate, `runtime`
  resolves and checks the OpenMP runtime, `sweep` builds every candidate.
- `alloy/evaluate/`: `link` builds whole programs from scope archives, `verify` checks candidates on fuzzed inputs,
  `timing` times them and links alloy-full.
- `alloy/`: `api` (`generate`, the entry point), `machine` (cores, cache), `report` (writes and loads `report.json`),
  `records` (the strict pydantic configuration of the timing, verdict, report and manifest records). Every compiler,
  flag and option is in `alloy/configuration_matrix.toml`, validated by the pydantic models of
  `alloy/configuration_matrix.py`.
- `examples/`: input programs for Alloy (dace numpy with symbolic sizes).
- `samples/`: A/B studies. Each holds a slow and a fast rendering of one kernel, the harness, and the setup that
  measured the gap.
- `tests/`: one file per module, plus the cross-compiler OpenMP link test.
- `docs/`: design decisions with build status, measurement rules, related work.

Tests: `pytest -m "not icx"` on a box without Intel oneAPI (each compiler is a pytest mark); CI installs gcc,
clang, oneAPI and the NVIDIA HPC SDK and runs everything, including the cross-compiler OpenMP link test.

Notes: `docs/design.md` (decisions), `docs/measurement.md` (A/B rules), `docs/related_work.md` (citations).
