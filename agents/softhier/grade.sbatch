#!/bin/bash -l
#SBATCH -A g34
#SBATCH -J softhier-grade
#SBATCH -t 04:00:00
# Grades folders on GVSoC inside the SoftHier v1 image, in parallel: each line of $LIST is "TASK FOLDER".
#   LIST=jobs.txt sbatch -p amdvega -w ault20 -c 16 --mem=32G -o grade-%j.out grade.sbatch
# With REFERENCE=1 each folder first gets the task's scalar reference kernel.c (the baseline).
set -uo pipefail
HERE=${HERE:-$(pwd)}
IMAGE=${IMAGE:-/scratch/ybudanaz/softhier/image/softhier-v1.sif}
grade() {
  set -- $1
  [ "${REFERENCE:-0}" = 1 ] && singularity exec -B /scratch/ybudanaz "$IMAGE" python3 "$HERE/host.py" reference "$1" "$2"
  singularity exec -B /scratch/ybudanaz "$IMAGE" python3 "$HERE/host.py" grade "$1" "$2"
}
export -f grade; export HERE IMAGE REFERENCE
xargs -a "${LIST:?a file of TASK FOLDER lines}" -P "${SLURM_CPUS_PER_TASK:-8}" -I{} bash -c 'grade "{}"'
