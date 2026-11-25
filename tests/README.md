# Alloy's tests

- **Reproducers stay.** A test written for a bug carries one comment line directly above it (above its decorators):

  ```python
  # Reproducer: <what broke, where> (<kernel, job or commit>)
  def test_...():
  ```

  A pruning pass never deletes a tagged test.
- **Per-row gates check a sample.** A test over every row of a shipped table (`intrinsics.toml`, the math kernels,
  `simt.toml`) takes `helpers.sample(rows)`: a fixed spread of the rows. The verify CLIs
  (`python -m alloy.isa.<table> verify`) check every row and record the verdicts the answers carry.
- **One fact, one test.** A test that only greps generated text for what a planted-bug test already proves fails
  (a wrong lane, a swapped operand) adds nothing; keep the planted-bug test.
