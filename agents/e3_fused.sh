#!/usr/bin/env bash
# E3 as one run of the bench's launch_fused.sbatch, for a site that admits one job per user (beverin). The run's
# 2-node slice: the first node serves MODEL through the bench's serve-only.sbatch with ACCESS=alps (a keyed
# RUN/serve/endpoint.json, which run_agent.py reads), the second runs the episodes of every study in STUDIES
# (agents/e3_episodes.sh, one study after the other) and stops the server when they end. Episodes only write
# submissions: SoftHier is graded on GVSoC and Tensix on the card afterwards (GRADE=0).
#   e3 2 <bench checkout> MODEL=oss120b STUDIES=softhier,tensix PYTHON=<workspace>/.venv/bin/python \
#       TT_DOCS_TREE=<tt-metal docs tree> -- bash ../alloy/agents/e3_fused.sh <run folder>
# CONFIGS and TOKENS pass through to agents/e3_episodes.sh; JOBS (default 16) episodes share the one server at once.
set -euo pipefail
ALLOY=$(cd "$(dirname "$0")/.." && pwd)
RUN=${1:?run folder}
MODEL=${MODEL:?the served model, as experiments.toml names it}
STUDIES=${STUDIES:-softhier,tensix}  # comma-separated: launch_fused.sbatch splits a line on spaces
mkdir -p "$RUN"
mapfile -t nodes < <(scontrol show hostnames "${SLURM_JOB_NODELIST:?not inside an allocation}")
(( ${#nodes[@]} == 2 )) || { echo "e3_fused: needs a 2-node slice, got ${#nodes[*]}" >&2; exit 2; }
# The server sees the first node as its whole allocation, as launch_fused.sbatch shows a run its slice.
(
  export SLURM_JOB_NODELIST=${nodes[0]} SLURM_NODELIST=${nodes[0]} SLURM_JOB_NUM_NODES=1 SLURM_NNODES=1 \
    SLURM_NTASKS=1 SLURM_NPROCS=1 SLURM_TASKS_PER_NODE=1 ACCESS=alps RUN_ROOT=$RUN HPCAGENT_BENCH_RUN_ID=serve
  exec bash "${HPCAGENT_BENCH_REPO:?the bench checkout}/hpcagent_bench/cluster/serve-only.sbatch"
) > "$RUN/serve.log" 2>&1 &
server=$!
trap 'kill "$server" 2>/dev/null; wait "$server" 2>/dev/null || true' EXIT
until [ -s "$RUN/serve/endpoint.json" ]; do
  kill -0 "$server" 2>/dev/null || { echo "e3_fused: the server exited before publishing" >&2; tail -40 "$RUN/serve.log" >&2; exit 1; }
  sleep 30
done
for study in ${STUDIES//,/ }; do
  mkdir -p "$RUN/$study"
  srun --overlap -N1 -n1 -w "${nodes[1]}" --cpus-per-task="${SLURM_CPUS_ON_NODE:-16}" \
    env GRADE=0 MODEL="$MODEL" JOBS="${JOBS:-16}" bash "$ALLOY/agents/e3_episodes.sh" "$study" "$RUN/$study" "$RUN/serve/endpoint.json"
done
