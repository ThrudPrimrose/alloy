#!/usr/bin/env bash
# Moves the hpcagent_bench pin in pyproject.toml to the head of its main branch (BENCH_BRANCH overrides) and the
# [tool.uv] dace override (development and CI; the dependency is bare) to the dace commit that bench commit pins,
# then relocks. The bench owns the dace pin, so Alloy grades on the dace the bench runs.
set -euo pipefail

root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
dace_url=https://github.com/spcl/dace.git
bench_url=https://github.com/spcl/HPCAgent-Bench.git

bench=$(git ls-remote "$bench_url" "refs/heads/${BENCH_BRANCH:-main}" | cut -f1)
[[ -n $bench ]] || { echo "bench branch head not found" >&2; exit 1; }
dace=$(curl -fsSL "https://raw.githubusercontent.com/spcl/HPCAgent-Bench/${bench}/pyproject.toml" |
    python3 -c 'import sys, tomllib; print(tomllib.load(sys.stdin.buffer)["tool"]["uv"]["sources"]["dace"]["rev"])')
[[ $dace =~ ^[0-9a-f]{40}$ ]] || { echo "the bench's dace pin not found" >&2; exit 1; }

sed -i -E "s#(${dace_url}@)[0-9a-f]{40}#\1${dace}#g; s#(${bench_url}@)[0-9a-f]{40}#\1${bench}#" "$root/pyproject.toml"
(cd "$root" && uv lock)

echo "bench ${bench}"
echo "dace  ${dace}"
