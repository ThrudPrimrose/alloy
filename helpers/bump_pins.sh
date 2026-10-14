#!/usr/bin/env bash
# Moves the hpcagent_bench pin in pyproject.toml to the head of its main branch (BENCH_BRANCH overrides) and every
# dace pin (the dependency and the [tool.uv] override that wins over the bench's own dace pin) to the head of dace
# extended, then relocks.
set -euo pipefail

root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
dace_url=https://github.com/spcl/dace.git
bench_url=https://github.com/spcl/HPCAgent-Bench.git

bench=$(git ls-remote "$bench_url" "refs/heads/${BENCH_BRANCH:-main}" | cut -f1)
[[ -n $bench ]] || { echo "bench branch head not found" >&2; exit 1; }
dace=$(git ls-remote "$dace_url" refs/heads/extended | cut -f1)
[[ -n $dace ]] || { echo "dace extended head not found" >&2; exit 1; }

sed -i -E "s#(${dace_url}@)[0-9a-f]{40}#\1${dace}#g; s#(${bench_url}@)[0-9a-f]{40}#\1${bench}#" "$root/pyproject.toml"
(cd "$root" && uv lock)

echo "bench ${bench}"
echo "dace  ${dace}"
