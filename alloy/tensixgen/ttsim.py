# Copyright 2026 ETH Zurich and the Alloy authors.
"""Generated Tensix programs run on ttsim: each program spelled for tt-metal 0.8x (the pinned image's), run under the
eval contract v2 by ``ttsim_host.py`` inside :data:`alloy.isa.tensix.IMAGE` on the simulator library
(:func:`alloy.isa.tensix.ttsim`), one container for every program given."""

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

from alloy.isa import tensix
from alloy.jsontype import Json
from alloy.tensixgen.split import Options
from alloy.tensixgen.tasks import programs

__all__ = ["HOST", "Verdict", "default_cache", "parse", "run", "run_tasks"]

HOST = pathlib.Path(__file__).with_name("ttsim_host.py")
#: The container's memory cap: the machine is shared, and the simulator of the whole grid stays well under it.
MEMORY = "4g"
TIMEOUT = 7200
PREFIX = "TENSIXGEN-VERDICT "


@dataclass(frozen=True, slots=True)
class Verdict:
    """One program's run: within the contract's tolerance, its max relative and absolute error, the cores it ran on,
    and the error that stopped it."""

    name: str
    ok: bool
    err: float | None = None
    abs: float | None = None
    cores: int = 0
    error: str = ""


def default_cache() -> pathlib.Path:
    return pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "alloy-ttsim"


def parse(stdout: str) -> list[Verdict]:
    return [Verdict(**json.loads(line[len(PREFIX) :])) for line in stdout.splitlines() if line.startswith(PREFIX)]


def run(folders: list[pathlib.Path], cache: pathlib.Path, image: str = tensix.IMAGE) -> list[Verdict]:
    """The programs in ``folders`` (spelled for tt-metal 0.8x) on ttsim, in this order; the torch wheel the host needs
    is cached under ``cache`` between runs."""
    if shutil.which("docker") is None:
        raise RuntimeError("docker is not on PATH: the programs run inside a tt-metal image")
    library = tensix.ttsim(cache)
    wheels = cache / "uv"
    wheels.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="alloy_tensixgen_", dir=cache) as tmp:
        work = pathlib.Path(tmp)
        shutil.copy(HOST, work / "ttsim_host.py")
        names = []
        for folder in folders:
            shutil.copytree(folder, work / "programs" / folder.name)
            names.append(f"/work/programs/{folder.name}")
        script = (
            "set -e; source /opt/venv/bin/activate; "
            "cp $(python3 -c 'import ttnn,os;print(os.path.dirname(ttnn.__file__))')"
            "/tt_metal/soc_descriptors/blackhole_140_arch.yaml /sim/soc_descriptor.yaml; "
            "(python3 -c 'import torch' 2>/dev/null || uv pip install -q --python /opt/venv/bin/python3 torch "
            "--index-url https://download.pytorch.org/whl/cpu); "
            f"python3 /work/ttsim_host.py {' '.join(names)}"
        )
        done = subprocess.run(
            ["docker", "run", "--rm", "--memory", MEMORY, "-v", f"{library.parent}:/sim", "-v", f"{work}:/work",
             "-v", f"{wheels}:/uvcache", "-e", "UV_CACHE_DIR=/uvcache",
             "-e", "TT_METAL_SIMULATOR=/sim/libttsim.so", "-e", "TT_METAL_SLOW_DISPATCH_MODE=1",
             # ttsim does not model SFPLOADMACRO; tt-metal then takes its plain SFPU path
             "-e", "TT_METAL_DISABLE_SFPLOADMACRO=1", image, "bash", "-c", script],
            capture_output=True, text=True, check=False, timeout=TIMEOUT,
        )  # fmt: skip
        for folder in folders:  # a gate case's output (ttsim_host.py: inputs.npz)
            got = work / "programs" / folder.name / "got.npy"
            if got.exists():
                shutil.copy(got, folder / "got.npy")
    found = parse(done.stdout)
    if done.returncode != 0 or len(found) != len(folders):
        raise RuntimeError(
            f"the host gave {len(found)} of {len(folders)} verdicts (exit {done.returncode}): {done.stderr[-2000:]}"
        )
    return found


def run_tasks(tasks: list[Json], cache: pathlib.Path, options: Options = Options()) -> list[Verdict]:
    """Each eval task's program, spelled for tt-metal 0.8x with ``options``, run on ttsim in one container."""
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="alloy_tensixgen_src_", dir=cache) as tmp:
        folders = [p.write(pathlib.Path(tmp) / p.name) for p in programs(tasks, options, "v08")]
        return run(folders, cache)
