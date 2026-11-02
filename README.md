# Alloy

Per-scope code generation backend for DaCe. Input: a dace numpy program with symbolic sizes (as an SDFG).
Alloy splits it into scopes, renders each scope under many codegen knobs, compilers and FP levels,
verifies every candidate, times the survivors, and links the best into one program plus a report. On
HPCAgent-Bench it is a user plugin (`alloy/hb_plugin`): agents give a manifest with C or NumPy and read the report.

    uv sync --extra dev

```python
import pathlib
from alloy import api
from alloy.frontend import inputs
from examples.two_scopes import two_scopes

manifest = inputs.load(pathlib.Path("examples/two_scopes.yaml"), "examples/two_scopes.py:two_scopes")
if __name__ == "__main__":  # Alloy's worker processes re-import this script
    result = api.generate(two_scopes.to_sdfg(), pathlib.Path("out"), manifest=manifest)  # result.report: report.md
```

As DaCe's backend no guard is needed: set `compiler.build_plugin = alloy-speculative` and call `sdfg.compile()`.

Extras: the core (outline, sweep, build) needs only DaCe. `bench` adds HPCAgent-Bench, which verification and
timing use for manifest inputs and the tolerance band. `nvgpu` / `amdgpu` add the matching cupy build. `dev` is
`bench` plus the test tools (CPU, what CI installs); `dev-nvidia` and `dev-amd` add the GPU extra.

Inputs come from an HPCAgent-Bench style manifest next to the program (`two_scopes.yaml`: sizes, a `fuzzed` range,
an `args` block); without one, candidates are built but not verified.

Layout:

- `alloy/frontend/`: `scopes` outlines a program, `inputs` draws its inputs from a bench manifest, `tree` prints the
  control-flow tree the report carries.
- `alloy/backend/`: `candidates` enumerates the sweep, `build` renders, compiles and checks one candidate, `runtime`
  resolves and checks the OpenMP runtime, `sweep` builds every candidate.
- `alloy/evaluate/`: `link` builds whole programs from scope archives, `verify` checks candidates on fuzzed inputs,
  `timing` times them and links alloy-full.
- `alloy/isa/`: the machine abstract math ISA (`ops.py`: load, store, gather, scatter, broadcast, +, -, *, /, %,
  fma, sqrt, min, max, abs, neg, select, lanewise reduction, integer & / << >> && ||, gen_mask, zero, and the
  transcendentals exp/sin/cos) spelled per ISA and dtype — f64/f32 everywhere, f16 where the hardware has it
  (AVX2 emulates through f32), i64/i32 for the integer ops — with fallback recipes where an op has no native
  instruction. `intrinsics.toml` is verified against the clang resource headers; both lookup directions;
  `python -m alloy.isa host|lookup|reverse|assist|kernel|validate|skeleton|ops|isas|schedule`. `validate.py` runs
  a row's intrinsic or recipe in a compiled kernel, natively or under `qemu-aarch64` when that is on PATH, or re-measures
  its tier, before an agent sees it; a row that did not run stays `unverified`, however it compiled;
  `hints.py` builds the do-it-yourself response from a scope's tasklets when emission fails;
  `schedules.py` emits compile-and-run-verified C skeletons per loop schedule, with the compiler
  flags that ask gcc/clang for the same shape.
  This is the bridge between DaCe's auto-vectorized intrinsic code and the math an agent reasons in.
- `alloy/heuristics/`: what Alloy picks without timing: `predict`, `prune`, `fission`, `fp`.
- `alloy/`: `api` (`generate`, the entry point), `dace_backend` (Alloy behind `SDFG.compile`), `gpu` (speculated
  threadblock shapes), `guidance` (advice for the scopes left short), `machine` (cores, cache), `report` (builds `report.json`, renders `report.md` from it, loads it back),
  `records` (the strict pydantic configuration of the timing, verdict, report and manifest records). Every compiler,
  flag and option is in `alloy/configuration_matrix.toml`, validated by the pydantic models of
  `alloy/configuration_matrix.py`.
- `examples/`: input programs for Alloy (dace numpy with symbolic sizes).
- `samples/`: A/B studies. Each holds a slow and a fast rendering of one kernel, the harness, and the setup that
  measured the gap.
- `tests/`: one file per module, plus the cross-compiler OpenMP link test.
- `docs/`: design decisions with build status, measurement rules, related work.

Tests: `pytest -m "not icx"` on a box without Intel oneAPI (each compiler is a pytest mark); CI installs gcc,
clang, oneAPI and the NVIDIA HPC SDK and runs all but the `avx512`, `cuda` and `hip` marks, including the
cross-compiler OpenMP link test.

Notes: `docs/design.md` (decisions), `docs/measurement.md` (A/B rules), `docs/related_work.md` (citations).

## How to extend it

A run goes `frontend/scopes` (outline), `backend/candidates` (the sweep), `heuristics/prune` (drop what cannot change
the code), `backend/sweep` and `build` (render and compile), `evaluate/verify` (fuzzed inputs), `evaluate/timing`
(screen and final reps, link `alloy_full`), `report`. Add to the step that owns the decision.

- **A compiler, FP level, ISA, tail or vector library.** Edit `alloy/configuration_matrix.toml`; add a field to its
  pydantic model in `alloy/configuration_matrix.py` only for a new kind of setting. `one_factor_at_a_time` sweeps what
  the file lists, and every candidate is verified, so no Python changes for a new row.
- **A sweep axis.** Add the factor to `Candidate` and its flips to `backend/candidates.py`, then tell `heuristics/prune`
  when the factor cannot change the object. The prune reason goes in the report, so an axis that looks useless shows up
  there.
- **An ISA row.** Add `[isa.<isa>.<dtype>.<op>]` to `alloy/isa/intrinsics.toml`, with the spelling checked against the
  compiler's headers; a composite needs a `recipe` and the `code` that states its operand order. A new op also goes in
  `OPS` in `alloy/isa/ops.py`, which holds the math, never a spelling. Run `python -m alloy.isa validate`: a row is
  compiled and executed natively, or under `qemu-aarch64` when that and `aarch64-linux-gnu-gcc` are on PATH. A row that
  only cross-compiled stays `unverified`. Do not mark a row verified by hand.
- **A math kernel.** `alloy/isa/mathkernels.py` and `helpers/mathfit.py`, which fits the coefficients. State the level
  (`strict`, `relaxed`, `fast`) and re-measure the ulp bound the row cites.
- **A verification rule.** `alloy/evaluate/verify.py`. A candidate is judged by its outputs on fuzzed inputs against the
  reference, so a new check must be able to fail a candidate that builds and runs.
- **A hint for agents.** `alloy/isa/hints.py` reads a scope's tasklets when emission fails; `alloy/guidance.py` advises
  on the scopes left short.
- **A bench tool or packet.** `alloy/hb_plugin`: the tool in `tools/alloy.py`, its judge half in `routes/alloy.py`, the
  packet in `plugin.toml`, prompt changes in `prompt/overlay.yaml`, and the agent-facing text in `skills/`. The judge
  half runs Alloy in a process of its own, because the judge's threads never fork.

After any change to what a scope builds, run the whole suite: `uv run pytest -m "not icx" -n 3 --maxfail=10`, and
`BENCH_BRANCH=<branch> bash helpers/bump_pins.sh` when the bench or DaCe pin moves.
