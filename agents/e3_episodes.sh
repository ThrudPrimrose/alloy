#!/usr/bin/env bash
# The E3 episodes of one study inside an allocation, shared by the ault launcher (agents/e3.sh) and the beverin fused
# run (agents/e3_fused.sh):
#   agents/e3_episodes.sh softhier|tensix RUN ENDPOINT_JSON
# RUN/episodes.txt lists "<task> <config>" lines; without it every task of the study's tasks.json runs under each of
# CONFIGS (default "none docs tool"). Each episode: run_agent.py with TOKENS (default 2500000) into
# RUN/submissions/<task>-<model>-<config>. GRADE=1 also grades a SoftHier submission on GVSoC in SOFTHIER_IMAGE
# (singularity); GRADE=0 leaves grading for later. PYTHON is the interpreter with alloy installed; JOBS episodes run
# at once (default SLURM_CPUS_PER_TASK, else 16). Tensix needs TT_DOCS_TREE (the pinned tt-metal docs tree).
set -euo pipefail
ALLOY=$(cd "$(dirname "$0")/.." && pwd)
STUDY=${1:?softhier or tensix}; RUN=${2:?run folder}; ENDPOINT=${3:?endpoint.json}
PYTHON=${PYTHON:-python3}
CONFIGS=${CONFIGS:-none docs tool}
TOKENS=${TOKENS:-2500000}
GRADE=${GRADE:-0}
JOBS=${JOBS:-${SLURM_CPUS_PER_TASK:-16}}
MODEL=${MODEL:-oss120b}
mkdir -p "$RUN/submissions"
cd "$RUN"
if [ ! -s episodes.txt ]; then
  tasks=$("$PYTHON" -c "import json,sys; print(' '.join(t['name'] for t in json.load(open(sys.argv[1]))))" \
    "$ALLOY/agents/$([ "$STUDY" = tensix ] && echo tensix/agents || echo softhier)/tasks.json")
  for task in $tasks; do for config in $CONFIGS; do echo "$task $config"; done; done > episodes.txt
fi
export ALLOY_REPO=$ALLOY
if [ "$STUDY" = softhier ]; then  # docs: the bench's docs-md-softhier pages; tensix: the pinned tt-metal tree
  mkdir -p docs && cp -r "$ALLOY"/alloy/hb_plugin/skills/docs-md-softhier-* docs/ && export DOCS_TREE=$RUN/docs
else
  export TT_DOCS_TREE=${TT_DOCS_TREE:?the pinned tt-metal docs tree}
  "$PYTHON" "$ALLOY/agents/tools/helptool.py" docs fetch
fi
episode() {
  set -- $1
  local out=$RUN/submissions/$1-$MODEL-$2
  "$PYTHON" "$ALLOY/agents/run_agent.py" "$1" "$2" "$out" --study "$STUDY" --endpoint "$ENDPOINT" --tokens "$TOKENS" \
    > "$out.log" 2>&1 || true
  if [ "$STUDY" = softhier ] && [ "$GRADE" = 1 ]; then
    singularity exec -B "$RUN" -B /scratch/ybudanaz "$SOFTHIER_IMAGE" python3 "$ALLOY/agents/softhier/host.py" grade \
      "$1" "$out" > "$out.verdict" 2>&1 || true
  fi
}
export -f episode; export RUN STUDY ENDPOINT PYTHON TOKENS GRADE MODEL ALLOY SOFTHIER_IMAGE="${SOFTHIER_IMAGE:-}"
xargs -a episodes.txt -P "$JOBS" -I{} bash -c 'episode "{}"'
