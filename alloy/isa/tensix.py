# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Tenstorrent Tensix rows (``tensix.toml``) and their verdicts (``tensix_verified.toml``).

A Tensix row is no intrinsic: it is the compute-kernel call that applies an op to a tile in DST, on the SFPU or the
FPU. Rows are verified by running them (``tensix_harness.py``) inside a tt-metal image on Tenstorrent's simulator
ttsim, or on a Blackhole; ``python -m alloy.isa.tensix verify`` does the first and records what it saw.

    python -m alloy.isa.tensix verify [--ttsim PATH] [--image REF]   # rerun every row on ttsim, rewrite verdicts
"""

import argparse
import datetime
import functools
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

__all__ = ["IMAGE", "ROWS_PATH", "Row", "Verdict", "rows", "verdicts", "verify"]

HERE = pathlib.Path(__file__).parent
ROWS_PATH = HERE / "tensix.toml"
VERDICTS_PATH = HERE / "tensix_verified.toml"
HARNESS = HERE / "tensix_harness.py"
#: The tt-metal release image the simulator runs (tt-metal 0.8x, ttnn wheel), pinned: ``latest-rc`` moves.
IMAGE = (
    "ghcr.io/tenstorrent/tt-metal/tt-metalium-ubuntu-22.04-release-amd64"
    "@sha256:254e24eea71325fe7c564dd8e5dd8568af1a402b6a668d6c9d9318c388a16b94"
)
TTSIM_RELEASE = "v1.16.0"
#: Relative error a row must stay under: f32 rows on the FPU read TF32 operands, so the f32 bound is loose.
TOLERANCE = {"f32": 1e-2, "bf16": 5e-2}
RUN_TIMEOUT = 3600


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class Row:
    """One way to apply ``op`` to a tile: a ``kind`` of kernel (unary on the SFPU, binary on the FPU, binary on the
    SFPU), its header under the compute API root, and its ``init`` and ``call`` (per version when tt-metal renamed
    them: ``{"v06": ..., "v08": ...}``)."""

    op: str
    kind: str
    unit: str
    header: str
    init: str | dict[str, str]
    call: str | dict[str, str]
    domain: tuple[float, float]
    note: str = ""


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class Verdict:
    op: str
    dtype: str
    unit: str
    ok: bool
    rel: float | None
    error: str = ""


@functools.lru_cache(maxsize=None, typed=True)
def table(path: pathlib.Path = ROWS_PATH) -> dict:
    return tomllib.loads(path.read_text())


def rows() -> tuple[Row, ...]:
    return tuple(Row(op=op, **row) for op, entries in table()["ops"].items() for row in entries)


def dtypes() -> tuple[str, ...]:
    return tuple(table()["target"]["dtypes"])


@functools.lru_cache(maxsize=None, typed=True)
def recorded(path: pathlib.Path = VERDICTS_PATH) -> dict:
    return tomllib.loads(path.read_text()) if path.is_file() else {}


def verdicts() -> dict[tuple[str, str, str], Verdict]:
    """``(op, dtype, unit)`` -> the recorded verdict of that row."""
    return {(v["op"], v["dtype"], v["unit"]): Verdict(**v) for v in recorded().get("verdicts", [])}


def spelled(value: str | dict[str, str], version: str) -> str:
    return value if isinstance(value, str) else value[version]


def harness_rows() -> list[dict]:
    """Every row at every dtype, as the harness reads them."""
    return [
        {"op": r.op, "dtype": d, "kind": r.kind, "unit": r.unit, "header": r.header, "init": r.init, "call": r.call,
         "domain": list(r.domain), "tol": TOLERANCE[d]}
        for r in rows()
        for d in dtypes()
    ]  # fmt: skip


def ttsim(cache: pathlib.Path) -> pathlib.Path:
    """The Blackhole ttsim library of :data:`TTSIM_RELEASE` with its SoC descriptor beside it, downloaded once."""
    folder = cache / f"bh-{TTSIM_RELEASE}"
    library = folder / "libttsim.so"
    if not library.is_file():
        folder.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/tenstorrent/ttsim/releases/download/{TTSIM_RELEASE}/libttsim_bh.so"
        subprocess.run(["curl", "-fsSL", "-o", str(library), url], check=True, timeout=600)
    return library


def run_harness(library: pathlib.Path, image: str) -> list[Verdict]:
    """The harness over every row inside ``image`` on the simulator ``library`` (its folder mounted as /sim); the
    Blackhole SoC descriptor is copied beside the library from the image, as tt-metal before 0.83 needs."""
    if shutil.which("docker") is None:
        raise RuntimeError("docker is not on PATH: the harness runs inside a tt-metal image")
    with tempfile.TemporaryDirectory(prefix="alloy_tensix_") as tmp:
        work = pathlib.Path(tmp)
        (work / "rows.json").write_text(json.dumps(harness_rows()))
        shutil.copy(HARNESS, work / "tensix_harness.py")
        script = (
            "set -e; source /opt/venv/bin/activate; "
            "cp $(python3 -c 'import ttnn,os;print(os.path.dirname(ttnn.__file__))')"
            "/tt_metal/soc_descriptors/blackhole_140_arch.yaml /sim/soc_descriptor.yaml; "
            "(python3 -c 'import torch' 2>/dev/null || uv pip install -q --python /opt/venv/bin/python3 torch "
            "--index-url https://download.pytorch.org/whl/cpu); "
            "python3 /work/tensix_harness.py /work/rows.json"
        )
        done = subprocess.run(
            ["docker", "run", "--rm", "--memory", "6g", "-v", f"{library.parent}:/sim", "-v", f"{work}:/work",
             "-e", "TT_METAL_SIMULATOR=/sim/libttsim.so", "-e", "TT_METAL_SLOW_DISPATCH_MODE=1",
             # ttsim does not model SFPLOADMACRO; tt-metal then takes its plain SFPU path
             "-e", "TT_METAL_DISABLE_SFPLOADMACRO=1", image, "bash", "-c", script],
            capture_output=True, text=True, check=False, timeout=RUN_TIMEOUT,
        )  # fmt: skip
    found = [
        Verdict(**json.loads(line.split(" ", 1)[1]))
        for line in done.stdout.splitlines()
        if line.startswith("TENSIX-VERDICT ")
    ]
    if done.returncode != 0 or len(found) != len(harness_rows()):
        raise RuntimeError(
            f"the harness gave {len(found)} of {len(harness_rows())} verdicts (exit {done.returncode}): "
            f"{done.stderr[-1500:]}"
        )
    return found


def verdicts_text(found: list[Verdict], library: pathlib.Path, image: str) -> str:
    digest = hashlib.sha256(library.read_bytes()).hexdigest()
    head = [
        "# Written by `python -m alloy.isa.tensix verify`: every tensix.toml row run on ttsim (simulated Blackhole).",
        f'run = "{datetime.datetime.now(datetime.UTC).date().isoformat()}"',
        f'image = "{image}"',
        f'ttsim = "{TTSIM_RELEASE} sha256:{digest}"',
        'note = "SFPLOADMACRO disabled (ttsim does not model it); f32 SFPU rows ran with fp32_dest_acc_en and UnpackToDestFp32, every row at HiFi4"',
        "",
    ]
    body = []
    for v in found:
        fields = {"op": v.op, "dtype": v.dtype, "unit": v.unit, "ok": v.ok, "rel": v.rel, "error": v.error or None}
        body += ["[[verdicts]]", *(f"{k} = {json.dumps(x)}" for k, x in fields.items() if x is not None), ""]
    return "\n".join(head + body)


def verify(cache: pathlib.Path, image: str = IMAGE) -> list[Verdict]:
    """Every row run on ttsim; the verdicts rewrite :data:`VERDICTS_PATH`."""
    library = ttsim(cache)
    found = run_harness(library, image)
    VERDICTS_PATH.write_text(verdicts_text(found, library, image))
    recorded.cache_clear()
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m alloy.isa.tensix", description=__doc__)
    parser.add_argument("command", choices=("verify",))
    parser.add_argument(
        "--cache",
        type=pathlib.Path,
        default=pathlib.Path(os.environ.get("XDG_CACHE_HOME", pathlib.Path.home() / ".cache")) / "alloy-ttsim",
    )
    parser.add_argument("--image", default=IMAGE)
    args = parser.parse_args(argv)
    found = verify(args.cache, args.image)
    failed = [v for v in found if not v.ok]
    for v in found:
        print(
            f"{v.op:6} {v.dtype:5} {v.unit:5} {'ok' if v.ok else 'FAIL'} {v.rel if v.rel is not None else v.error[:120]}"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
