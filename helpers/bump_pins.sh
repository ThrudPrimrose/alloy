#!/usr/bin/env bash
# Moves the hpcagent-bench pin ([tool.uv.sources]) in pyproject.toml to the head of its main branch (BENCH_BRANCH
# overrides), moves each sibling package's `>=` bound in [project] to its latest PyPI release (a package not on PyPI
# yet keeps its bound), then relocks: uv installs the released versions pip installs.
set -euo pipefail

root=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
bench_url=https://github.com/spcl/HPCAgent-Bench.git

bench=$(git ls-remote "$bench_url" "refs/heads/${BENCH_BRANCH:-main}" | cut -f1)
[[ -n $bench ]] || { echo "bench branch head not found" >&2; exit 1; }

sed -i -E "s#(${bench_url}\", rev = \")[0-9a-f]{40}#\1${bench}#" "$root/pyproject.toml"
for package in hpcagent-bench dace-extended dace-relayout; do
    latest=$(curl -fsSL "https://pypi.org/pypi/${package}/json" 2>/dev/null |
        python3 -c 'import sys, json; print(json.load(sys.stdin)["info"]["version"])' 2>/dev/null) || latest=""
    [[ -z $latest ]] && { echo "${package}: not on PyPI, bound kept"; continue; }
    sed -i -E "s#\"${package}>=[^\";]*#\"${package}>=${latest}#g" "$root/pyproject.toml"
    echo "${package} >= ${latest}"
done
(cd "$root" && uv lock)

echo "bench ${bench}"
