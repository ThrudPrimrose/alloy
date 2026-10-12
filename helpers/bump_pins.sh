#!/usr/bin/env bash
# Moves the hpcagent_bench pin in pyproject.toml to the head of its main branch (BENCH_BRANCH overrides) and the dace
# pin to the dace commit that bench head pins, then relocks. uv reads the bench's [tool.uv.sources], so the two dace
# pins must agree; a newer dace than the bench's lands here after the bench moves to it.
set -euo pipefail

root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
dace_url=https://github.com/spcl/dace.git
bench_url=https://github.com/spcl/HPCAgent-Bench.git

bench=$(git ls-remote "$bench_url" "refs/heads/${BENCH_BRANCH:-main}" | cut -f1)
[[ -n $bench ]] || { echo "bench branch head not found" >&2; exit 1; }
dace=$(gh api "repos/spcl/HPCAgent-Bench/contents/pyproject.toml?ref=$bench" -H "Accept: application/vnd.github.raw" |
    grep -oE 'spcl/dace\.git", rev = "[0-9a-f]{40}' | grep -oE '[0-9a-f]{40}$')

sed -i -E "s#(${dace_url}@)[0-9a-f]{40}#\1${dace}#; s#(${bench_url}@)[0-9a-f]{40}#\1${bench}#" "$root/pyproject.toml"
(cd "$root" && uv lock)

extended=$(git ls-remote "$dace_url" refs/heads/extended | cut -f1)
echo "bench ${bench}"
echo "dace  ${dace}"
[[ $extended == "$dace" ]] || echo "note: dace extended is at ${extended}; bump the bench pin first to take it" >&2
