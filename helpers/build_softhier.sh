#!/bin/bash
# Build the SoftHier v1 stack the rows of alloy/isa/softhier.toml run on, from alloy/isa/softhier_pins.toml, into one
# prefix: GVSoC with the target pulp.chips.soft_hier_old.flex_cluster, SystemC, DRAMSys, the softhier-sdk, the GCC 14
# RISC-V toolchain, and a Python venv for GVSoC's launcher. Run it inside the pinned base image with the prefix at the
# path the image will hold it (helpers/build_softhier_image.sh does both); a GVSoC install is not relocatable.
#
#   helpers/build_softhier.sh <alloy checkout> [prefix=/opt/softhier] [jobs=16]
set -euo pipefail
ALLOY=$(cd "${1:?the alloy checkout}" && pwd)
PREFIX=${2:-/opt/softhier}
JOBS=${3:-16}
PINS=$ALLOY/alloy/isa/softhier_pins.toml
BUILD=${TMPDIR:-/tmp}/softhier-build-$$
mkdir -p "$PREFIX" "$BUILD"
cd "$PREFIX"

pin() {  # pin <table> <key>: one value of the pins file
    python3 -c 'import sys, tomllib; t = tomllib.load(open(sys.argv[1], "rb")); print(t[sys.argv[2]][sys.argv[3]])' \
        "$PINS" "$1" "$2"
}
fetch() {  # fetch <dir> <url> <commit>: a clone at exactly that commit
    [ -d "$1/.git" ] || git clone -q "$2" "$1"
    git -C "$1" fetch -q origin "$3" 2>/dev/null || git -C "$1" fetch -q origin
    git -C "$1" checkout -q --detach "$3"
}

# Python: uv, the build tools, and the launcher's packages (the `softhier` extra of Alloy's pyproject.toml)
curl -fsSL "https://github.com/astral-sh/uv/releases/download/$(pin python uv)/uv-x86_64-unknown-linux-gnu.tar.gz" | \
    tar -xz -C "$BUILD"
UV=$BUILD/uv-x86_64-unknown-linux-gnu/uv
[ -x venv/bin/python ] || "$UV" venv -q --python /usr/bin/python3 venv
python3 - "$PINS" "$ALLOY/pyproject.toml" > "$BUILD/requirements.txt" <<'EOF'
import sys, tomllib
pins = tomllib.load(open(sys.argv[1], "rb"))
project = tomllib.load(open(sys.argv[2], "rb"))
print("\n".join(pins["python"]["build"] + project["project"]["optional-dependencies"]["softhier"]))
EOF
"$UV" pip install -q --python venv/bin/python -r "$BUILD/requirements.txt"
export PATH=$PREFIX/venv/bin:$PATH CMAKE=cmake

# Sources
fetch gvsoc "$(pin gvsoc url)" "$(pin gvsoc commit)"
git -C gvsoc submodule update -q --init --recursive
python3 - "$PINS" <<'EOF'
import subprocess, sys, tomllib
expected = tomllib.load(open(sys.argv[1], "rb"))["gvsoc"]["submodules"]
for name, commit in expected.items():
    found = subprocess.run(["git", "-C", f"gvsoc/{name}", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if found != commit:
        sys.exit(f"gvsoc/{name} is at {found}, the pins say {commit}")
EOF
fetch softhier-sdk "$(pin sdk url)" "$(pin sdk commit)"
[ -L gvsoc/soft_hier_sdk ] || ln -s ../softhier-sdk gvsoc/soft_hier_sdk
grep -q softhier_old.mk gvsoc/Makefile || echo "include soft_hier_sdk/softhier_old.mk" >> gvsoc/Makefile

# The GCC 14 RISC-V toolchain, checked against its digest
if [ ! -x softhier-sdk/toolchain/install/bin/riscv32-unknown-elf-gcc ]; then
    mkdir -p softhier-sdk/toolchain
    curl -fsSL -o "$BUILD/toolchain.tar.xz" "$(pin toolchain url)"
    echo "$(pin toolchain sha256)  $BUILD/toolchain.tar.xz" | sha256sum -c -
    tar -xf "$BUILD/toolchain.tar.xz" -C softhier-sdk/toolchain
fi

# SystemC, then DRAMSys built against it (the library gvsoc ships needs SystemC 2.3)
fetch "$BUILD/systemc" "$(pin systemc url)" "$(pin systemc commit)"
if [ ! -e systemc/lib64/libsystemc.so ]; then
    cmake -S "$BUILD/systemc" -B "$BUILD/systemc-build" -DCMAKE_CXX_STANDARD=17 -DCMAKE_INSTALL_PREFIX="$PREFIX/systemc" \
        -DCMAKE_INSTALL_LIBDIR=lib64 > /dev/null
    cmake --build "$BUILD/systemc-build" -j "$JOBS" > /dev/null
    cmake --install "$BUILD/systemc-build" > /dev/null
fi
export SYSTEMC_HOME=$PREFIX/systemc
mkdir -p gvsoc/third_party/DRAMSys
if [ ! -e gvsoc/third_party/DRAMSys/libDRAMSys_Simulator.so ]; then
    fetch "$BUILD/DRAMSys" "$(pin dramsys url)" "$(pin dramsys commit)"
    git -C "$BUILD/DRAMSys" apply "$PREFIX/gvsoc/add_dramsyslib_patches/build_dynlib_from_github_dramsys5/patch"
    cmake -S "$BUILD/DRAMSys" -B "$BUILD/DRAMSys-build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS=-fPIC \
        -DCMAKE_C_FLAGS=-fPIC -DDRAMSYS_USE_FETCH_CONTENT_SYSTEMC=OFF \
        -DSystemCLanguage_DIR="$SYSTEMC_HOME/lib64/cmake/SystemCLanguage" > /dev/null
    cmake --build "$BUILD/DRAMSys-build" -j "$JOBS" > /dev/null
    cp "$BUILD/DRAMSys-build/lib/libDRAMSys_Simulator.so" gvsoc/third_party/DRAMSys/
fi
[ -d gvsoc/core/models/memory/dramsys_configs ] || \
    cp -r gvsoc/add_dramsyslib_patches/dramsys_configs gvsoc/core/models/memory/
export LD_LIBRARY_PATH=$PREFIX/gvsoc/third_party/DRAMSys:$SYSTEMC_HOME/lib64:${LD_LIBRARY_PATH:-}

# GVSoC for the v1 configuration; the SDK's headers take the v1 flex_cluster_arch.h beside themselves
python3 "$ALLOY/alloy/isa/softhier_harness.py" arch "$ALLOY/alloy/isa/softhier.toml" > "$PREFIX/alloy_v1.py"
(cd gvsoc && set +u && source sourceme.sh && set -u && \
    make sh-old-hw cfg="$PREFIX/alloy_v1.py" CMAKE_FLAGS="-j $JOBS" > "$BUILD/gvsoc-build.log" 2>&1) || \
    { tail -40 "$BUILD/gvsoc-build.log"; exit 1; }
venv/bin/python softhier-sdk/utilities/config.py "$PREFIX/alloy_v1.py" --output-dir softhier-sdk/runtime/runtime/include
rm -rf gvsoc/build "$BUILD"
cat > env.sh <<ENV
export SOFTHIER_SDK=$PREFIX/softhier-sdk SOFTHIER_GVSOC=$PREFIX/gvsoc SYSTEMC_HOME=$PREFIX/systemc
export LD_LIBRARY_PATH=$PREFIX/gvsoc/third_party/DRAMSys:$PREFIX/systemc/lib64:\${LD_LIBRARY_PATH:-}
export PATH=$PREFIX/venv/bin:$PREFIX/gvsoc/install/bin:$PREFIX/softhier-sdk/toolchain/install/bin:\$PATH
ENV

# Smoke test: the SDK's hello world on the v1 configuration, every cluster in turn
SMOKE=$(mktemp -d)
SDK=$PREFIX/softhier-sdk/runtime/runtime
APP=$PREFIX/softhier-sdk/examples/SoftHier/software/test
"$PREFIX/softhier-sdk/toolchain/install/bin/riscv32-unknown-elf-gcc" -I "$SDK/include" -I "$APP/include" \
    -T "$SDK/flex_memory.ld" -nostartfiles -mabi=ilp32d -mcmodel=medlow -march=rv32imafdv_zfh -O3 -ffast-math \
    -fno-builtin -fno-tree-vectorize -fno-common -ffunction-sections -Wl,--gc-sections -o "$SMOKE/softhier.elf" \
    "$SDK/flex_start.s" "$APP/main.c" 2> /dev/null
(cd "$SMOKE" && SOFTHIER_ARCH_FILE=$PREFIX/alloy_v1.py "$PREFIX/gvsoc/install/bin/gvsoc" \
    --target="$(pin gvsoc target)" --binary softhier.elf --work-dir "$SMOKE" run) | grep "Hello World"
rm -rf "$SMOKE"
echo "SoftHier v1 stack ready in $PREFIX"
