# Measurement rules

Rules learned while building `samples/index_width`. Every Alloy sweep and sample follows them.

## Every arm runs on the same buffers

Giving each arm its own output buffer produced fake effects of 20-35%:

- stencil2d `all32` looked 0.80x faster;
- stencil3d `int64` looked 0.70x faster.

Reversing the arm order flipped both, and sharing one set of buffers made both vanish. The cause is buffer placement
(cache-set conflicts, 4K aliasing), not the code being compared (Mytkowicz et al., ASPLOS'09; see
`related_work.md`).

How to apply this:

- One input set and one output buffer for all arms.
- Alternate the arms back to back, one warmup, then N reps.
- Before claiming a win, re-run it with the arm order reversed.
- Assert that every arm's output is bit-identical to the reference arm's (or within the bench tolerance for FP levels).

## Reporting

- Median plus a distribution-free 95% CI from order statistics (Hoefler and Belli, SC'15).
- Report the setup with every number: CPU, compiler versions, flags, sizes, threads, DaCe commit.
- Every interesting win or loss becomes an A/B folder `samples/<name>/` holding:
  - the bad and the good generated code;
  - a harness that reproduces the result from that folder alone;
  - a README with the result table, the cause, and the setup.

## Recorded results

- `samples/index_width` (10-08):
  - int32 index helpers combined with int64 loop counters cost gcc its vectorization, 1.5-3x slower.
  - int32 counters alone are neutral.
  - No int32 win. The documented -26% (dace `b2d2993514`) did not reproduce.
