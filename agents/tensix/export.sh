#!/usr/bin/env bash
# Copies the Tenstorrent study (this folder) into an alloy-tenstorrent checkout, whose .daisy/ workflows run it on the
# Blackhole card on a push (Daisytuner's service watches that repository). alloy is the source; the export notes the
# alloy commit in agents/FROM_ALLOY. The runner and the help tools stay in alloy (agents/run_agent.py, agents/tools):
# they run on ault, not on the card.
#   agents/tensix/export.sh ~/Work/alloy-tenstorrent    # then commit and push there (agents or rows branch)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
TREE=${1:?an alloy-tenstorrent checkout}
for part in agents rows; do
  rsync -a --delete --exclude verdicts.json --exclude venv/ --exclude __pycache__/ --exclude .ttnn_runtime_artifacts/ \
    --exclude sfpi.txz "$HERE/$part/" "$TREE/$part/"
done
echo "alloy $(git -C "$HERE" rev-parse HEAD)" > "$TREE/agents/FROM_ALLOY"
