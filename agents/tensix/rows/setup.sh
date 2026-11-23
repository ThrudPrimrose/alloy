#!/bin/bash
# Build step: a Python 3.10 environment with the ttnn 0.63.0 wheel (the container has tt-metal's C++ tree, no ttnn).
# Exit codes: 10 uv, 11 venv, 12 torch, 13 ttnn, 41-49 import (see the end), 128+ a signal at import, 15 no sfpi compiler, 16 a missing shared library.
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh || exit 10
uv venv --clear -p 3.10 venv || exit 11
uv pip install -q --python venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu || exit 12
uv pip install -q --python venv/bin/python ttnn==0.63.0 || exit 13
# The wheel exits at import without the sfpi compiler at /opt/tenstorrent/sfpi: link the container's, or fetch 6.21.0.
if [ ! -d /opt/tenstorrent/sfpi ]; then
    mkdir -p /opt/tenstorrent || exit 15
    if [ -d /tenstorrent/tt-metalium/runtime/sfpi ]; then
        ln -s /tenstorrent/tt-metalium/runtime/sfpi /opt/tenstorrent/sfpi || exit 15
    else
        curl -fsSL -o sfpi.txz https://github.com/tenstorrent/sfpi/releases/download/v6.21.0/sfpi_6.21.0_x86_64.txz &&
            tar xJf sfpi.txz -C /opt/tenstorrent || exit 15
    fi
fi
ls /opt/tenstorrent/sfpi/compiler/bin | head -3
site=$(venv/bin/python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"])')
if ldd "$site"/ttnn/_ttnn*.so "$site"/ttnn/build/lib/*.so 2>&1 | grep "not found"; then exit 16; fi
# The wheel brings its own kernel sources and libraries: the container's TT_METAL_HOME, PYTHONPATH and
# LD_LIBRARY_PATH would point it at the container's tree instead.
env -u TT_METAL_HOME -u PYTHONPATH -u LD_LIBRARY_PATH venv/bin/python -c 'import ttnn; print("ttnn", ttnn.__file__)' \
    >import.log 2>&1
rc=$?
tail -40 import.log
[ $rc -eq 0 ] && exit 0
[ $rc -ge 128 ] && exit $rc
# The log is behind a login: the exit code names the error class.
n=41
for pattern in ModuleNotFoundError "undefined symbol" "cannot open shared object" "GLIBC" "Permission denied\|Read-only" \
    "SFPI\|sfpi" "seems to not exist" "numpy"; do
    grep -q "$pattern" import.log && exit $n
    n=$((n + 1))
done
exit 49
