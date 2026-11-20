#!/bin/bash
# Runs every program folder of a prepared gate on ault in the SoftHier v1 image, then fetches the logs:
#   gate/ault.sh <local gate folder> <run name>
# One Slurm job builds and runs the folders in parallel; this script waits for it.
set -euo pipefail
LOCAL=$(cd "$1" && pwd)
REMOTE=/scratch/ybudanaz/dsh-codegen-2026-11-19/$2
IMAGE=/scratch/ybudanaz/softhier/image/softhier-v1.sif
rsync -a --delete "$LOCAL/" "ault:$REMOTE/"
ssh ault "cat > $REMOTE/run.sbatch" <<SBATCH
#!/bin/bash
#SBATCH -J dsh-gate -N 1 -c 8 -t 1:00:00 --output=$REMOTE/slurm-%j.out
for folder in $REMOTE/*/; do
    [ -f \$folder/build_run.sh ] || continue
    singularity exec -B $REMOTE $IMAGE \$folder/build_run.sh > \$folder/build_run.log 2>&1 &
done
wait
SBATCH
JOB=$(ssh ault "sbatch --parsable -p amdrtx --mem=0 --exclude=ault03,ault18,ault19,ault21 $REMOTE/run.sbatch")
echo "job $JOB"
while ssh ault "squeue -h -j $JOB" | grep -q .; do sleep 30; done
rsync -a --include='*/' --include='build_run.log' --include='gvsoc.out' --exclude='*' "ault:$REMOTE/" "$LOCAL/"
