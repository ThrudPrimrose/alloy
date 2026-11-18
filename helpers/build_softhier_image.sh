#!/bin/bash
# The SoftHier v1 image without fakeroot: build the stack inside the pinned base image with the prefix bound at
# /opt/softhier, copy it into a sandbox of the base, and pack the sandbox as a SIF. Prints the image's sha256, which
# `python -m alloy.isa.softhier record --image` writes beside the verdicts. Run on a compute node:
#   helpers/build_softhier_image.sh <alloy checkout> <work folder> [jobs=16]
set -euo pipefail
ALLOY=$(cd "${1:?the alloy checkout}" && pwd)
WORK=$(mkdir -p "${2:?a work folder}" && cd "$2" && pwd)
JOBS=${3:-16}
BASE=$(sed -n 's/^image = "\(.*\)"/\1/p' "$ALLOY/alloy/isa/softhier_pins.toml")  # [base] image
export SINGULARITY_CACHEDIR=$WORK/cache SINGULARITY_TMPDIR=${TMPDIR:-/tmp}
[ -f "$WORK/base.sif" ] || singularity pull "$WORK/base.sif" "$BASE"
mkdir -p "$WORK/stack"
singularity exec -B "$WORK/stack:/opt/softhier" -B "$ALLOY:/opt/alloy" "$WORK/base.sif" \
    /opt/alloy/helpers/build_softhier.sh /opt/alloy /opt/softhier "$JOBS"
rm -rf "$WORK/sandbox"
singularity build -F --sandbox "$WORK/sandbox" "$WORK/base.sif" > /dev/null
cp -a "$WORK/stack" "$WORK/sandbox/opt/softhier"
echo ". /opt/softhier/env.sh" > "$WORK/sandbox/.singularity.d/env/90-softhier.sh"
singularity build -F "$WORK/softhier-v1.sif" "$WORK/sandbox" > /dev/null
rm -rf "$WORK/sandbox"
sha256sum "$WORK/softhier-v1.sif"
