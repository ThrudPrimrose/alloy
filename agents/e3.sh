#!/usr/bin/env bash
# E3 on a study outside the training data: oss120b episodes for every task x configuration (none, docs, tool), each
# with the 2.5M-token budget, against the vLLM endpoint on ault25. From the laptop, in an alloy checkout:
#   agents/e3.sh softhier|tensix ENDPOINT_RUN_DIR [TASKS...]   # ENDPOINT_RUN_DIR: /scratch/ybudanaz/vllm/run-<serve id>
# softhier: each submission is graded and timed on GVSoC in the same job (submissions/<name>.verdict). tensix: files
# only; copy submissions/ into agents/tensix/agents/submissions, export (agents/tensix/export.sh) and push the agents
# branch of alloy-tenstorrent, which grades and times them on the card.
# CONFIGS="none docs tool" and TOKENS=2500000 by default. Ships alloy at HEAD (committed files only), builds its
# environment in the job, and prints the job id and the run folder. The serve job must be running.
set -euo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
STUDY=${1:?softhier or tensix}; ENDPOINT=${2:?the serve job run folder, holding endpoint.json}; shift 2
CONFIGS=${CONFIGS:-none docs tool}
TOKENS=${TOKENS:-2500000}
RUN=/scratch/ybudanaz/agents/e3-$STUDY/$(date +%Y%m%d-%H%M%S)-$(git -C "$HERE" rev-parse --short HEAD)
ssh ault "mkdir -p $RUN"
git -C "$HERE" archive --prefix=alloy/ HEAD | ssh ault "tar xf - -C $RUN"
[ $# -eq 0 ] || for task in "$@"; do for config in $CONFIGS; do echo "$task $config"; done; done \
  | ssh ault "cat > $RUN/episodes.txt"  # without TASKS, agents/e3_episodes.sh runs every task of the study
ssh ault "cat > $RUN/job.sh" <<EOF
#!/bin/bash -l
set -uo pipefail
cd $RUN
export UV_CACHE_DIR=/scratch/ybudanaz/.cache/uv
~/.local/bin/uv venv -q --python 3.12 venv && ~/.local/bin/uv pip install -q --python venv/bin/python -e alloy || exit 3
PYTHON=$RUN/venv/bin/python GRADE=1 SOFTHIER_IMAGE=/scratch/ybudanaz/softhier/image/softhier-v1.sif \\
  TT_DOCS_TREE=/scratch/ybudanaz/.cache/tt-metal-v0.63.0 CONFIGS="$CONFIGS" TOKENS=$TOKENS \\
  bash alloy/agents/e3_episodes.sh $STUDY $RUN $ENDPOINT/endpoint.json
EOF
ssh ault "sbatch --parsable -A g34 -p amdvega -w ault20 -c 16 --mem=48G -t 04:00:00 -J e3-$STUDY -o $RUN/e3.out $RUN/job.sh"
echo "$RUN"
