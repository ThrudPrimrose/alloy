# Index width: int64 vs int32 indices in the readable CPU codegen

Two DaCe knobs set the integer width of the generated index math:

- `compiler.cpu.codegen_params.index_ctype`: type of the `<array>_idx` helpers (`int64` default, `int32`).
- `compiler.cpu.codegen_params.loop_index_type`: type of map loop counters (`inferred` = `int64_t` here, `int32`).

Four arms per kernel, code in `code/<kernel>/<arm>.cpp`:

| arm | helpers | counters |
|---|---|---|
| `int64` (default) | `int64_t` | `int64_t` |
| `counters32` | `int64_t` | `int32_t` |
| `helpers32` | `int32_t` | `int64_t` |
| `all32` | `int32_t` | `int32_t` |

## Result

No int32 win. `helpers32` is the bad rendering; `int64` is the good one.

- **Bad: `helpers32`.** gcc is 1.5x to 3.0x slower on row gather and both stencils, at 1 thread and at every size.
  clang is up to 1.6x slower.
- **`all32` with clang** is up to 1.49x slower (stencil3d, cache-resident) and 1.40x slower (row gather).
- **`counters32`** is neutral: within +-3% everywhere at 1 thread.
- **Element gather** is neutral in every arm. The cost there is the random load, not the index math.

1 thread, ratio to `int64` (lower is faster):

| kernel | compiler | cache | screen | large |
|---|---|---|---|---|
| row_gather | gcc helpers32 | 2.67 | 2.40 | 2.25 |
| row_gather | clang all32 | 1.20 | 1.40 | 1.35 |
| stencil2d | gcc helpers32 | 2.98 | 1.69 | 1.49 |
| stencil3d | gcc helpers32 | 2.35 | 1.79 | 1.82 |
| stencil3d | clang all32 | 1.49 | 1.12 | 1.07 |

Full tables with medians and 95% CIs: `results_t1.md`, `results_t16.md`.

## Why helpers32 is slow

The counters are `int64_t`; the helper takes `int32_t`. Every access truncates the counter, and the 32-bit
wrap makes the address non-affine to the vectorizer. gcc 15.2 on `code/stencil2d`:

    int64.cpp:      loop vectorized using 64 byte vectors
    helpers32.cpp:  missed: couldn't vectorize loop
                    missed: not vectorized: data ref analysis failed: a_index_35 = *_34;

## The documented -26% does not reproduce

Commit `b2d2993514` (dace, 2026-07-16) recorded "gcc/gather -26% for int32". Its harness was not kept.
In this sample, giving each arm its OWN buffers produced spurious effects of 20% to 35% (stencil2d `all32`
0.80x, stencil3d `int64` 0.70x). Reversing the arm order flipped them, and sharing one set of buffers
across arms made them vanish. The harness here therefore runs every arm on the same buffers.

## Setup

- AMD Ryzen 7 8845HS (Zen 4, 8 cores / 16 threads, 16 MiB L3), 12 GiB RAM, Linux 7.0.
- g++ 15.2.0 and clang++ 21.1.8 (clang 22 has no `libomp-22-dev` on this box), flags `-O3 -march=native`,
  CMake Release build through DaCe.
- DaCe extended `1c1cdc14d4`, generator `experimental_readable`, Python 3.13 in the Alloy uv venv.
- Sizes: cache ~0.5 MiB per array with an in-kernel repeat `T`, screen ~4x L3, large ~256 MiB per array.
- 20 reps per arm after one warmup, arms alternating back to back; median and distribution-free 95% CI.
- Every arm's output equals the `int64` arm's output bit for bit (asserted).

## Reproduce

    cd samples/index_width
    OMP_NUM_THREADS=1  PYTHONHASHSEED=0 ../../.venv/bin/python run.py > results_t1.md
    OMP_NUM_THREADS=16 PYTHONHASHSEED=0 ../../.venv/bin/python run.py > results_t16.md
