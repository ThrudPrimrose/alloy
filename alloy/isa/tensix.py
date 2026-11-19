# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Tenstorrent Tensix rows (``tensix.toml``) and their verdicts (``tensix_verified.toml``).

A Tensix row is no intrinsic: it is the compute-kernel call that applies an op to a tile in DST, on the SFPU or the
FPU. Rows are verified by running them (``tensix_harness.py``) inside a tt-metal image on Tenstorrent's simulator
ttsim, or on a Blackhole; ``python -m alloy.isa.tensix verify`` does the first and records what it saw.

    python -m alloy.isa.tensix verify [--ttsim PATH] [--image REF]   # rerun every row on ttsim, rewrite verdicts
"""

import argparse
import dataclasses
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

__all__ = [
    "CARD_PATH",
    "IMAGE",
    "ROWS_PATH",
    "Row",
    "Rung",
    "Verdict",
    "card_line",
    "card_verdicts",
    "digest",
    "rows",
    "rungs",
    "verdicts",
    "verify",
]

HERE = pathlib.Path(__file__).parent
ROWS_PATH = HERE / "tensix.toml"
VERDICTS_PATH = HERE / "tensix_verified.toml"
#: The rows measured on a Blackhole card with tt-metal 0.63 (variant card-0.63), beside ttsim's (variant ttsim-0.8x).
CARD_PATH = HERE / "tensix_card.toml"
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
    #: Added after the last recorded ttsim run: the CI job runs it, and ``verify`` records it.
    pending: bool = False


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class Verdict:
    """One row's run at one dtype; ``digest`` is :func:`digest` of the row as it ran."""

    op: str
    dtype: str
    unit: str
    ok: bool
    rel: float | None
    error: str = ""
    digest: str = ""
    #: A card record's max absolute error, input range, and the probe that measured it (ttsim records leave them out).
    abs: float | None = None
    domain: tuple[float, float] | None = None
    source: str = ""


@functools.lru_cache(maxsize=None, typed=True)
def table(path: pathlib.Path = ROWS_PATH) -> dict:
    return tomllib.loads(path.read_text())


def rows() -> tuple[Row, ...]:
    return tuple(Row(op=op, **row) for op, entries in table()["ops"].items() for row in entries)


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class Rung:
    """A math kernel for ``op`` written on SFPU lanes (SFPI), for when the tile call is less accurate than the caller
    needs: its inline source, the calls that run it on DST tile 0, and the error measured on a Blackhole."""

    op: str
    name: str
    dtype: str
    unit: str
    #: Bound in ulp from the card run: max relative error times 2^24.
    error_ulp: float
    #: Where its error was measured: tt-metal version, device, date, and the run's commit.
    card: str
    init: str
    call: str
    code: str
    note: str = ""


def rungs(op: str, dtype: str) -> tuple[Rung, ...]:
    """The SFPI math kernels of ``op`` at ``dtype``, most accurate first."""
    found = (Rung(op=name, **r) for name, entries in table().get("rungs", {}).items() for r in entries)
    return tuple(sorted((r for r in found if r.op == op and r.dtype == dtype), key=lambda r: r.error_ulp))


def dtypes() -> tuple[str, ...]:
    return tuple(table()["target"]["dtypes"])


@functools.lru_cache(maxsize=None, typed=True)
def recorded(path: pathlib.Path = VERDICTS_PATH) -> dict:
    return tomllib.loads(path.read_text()) if path.is_file() else {}


def digest(row: Row, dtype: str) -> str:
    """What a run of ``row`` at ``dtype`` checked: the kernel kind, unit, header, calls, inputs, and bound."""
    checked = [row.kind, row.unit, row.header, row.init, row.call, list(row.domain), dtype, TOLERANCE[dtype]]
    return hashlib.sha256(json.dumps(checked).encode()).hexdigest()[:16]


def current(path: pathlib.Path) -> dict[tuple[str, str, str], Verdict]:
    """``(op, dtype, unit)`` -> the verdict recorded in ``path`` of that row as it is now: a record of a row changed
    since its run is stale and left out, so the row is unverified until it runs again."""
    now = {(r.op, d, r.unit): digest(r, d) for r in rows() for d in dtypes()}
    found = (Verdict(**v) for v in recorded(path).get("verdicts", []))
    return {(v.op, v.dtype, v.unit): v for v in found if now.get((v.op, v.dtype, v.unit)) == v.digest}


def verdicts(path: pathlib.Path = VERDICTS_PATH) -> dict[tuple[str, str, str], Verdict]:
    """The ttsim verdicts (variant ttsim-0.8x) of the rows as they are now."""
    return current(path)


def card_verdicts() -> dict[tuple[str, str, str], Verdict]:
    """The card measurements (variant card-0.63) of the rows as they are now."""
    return current(CARD_PATH)


def card_line(row: Row, dtype: str) -> str:
    """The card-0.63 record of ``row`` at ``dtype`` as one line, or "" when the card has no current record of it."""
    verdict = card_verdicts().get((row.op, dtype, row.unit))
    if verdict is None or verdict.domain is None:
        return ""
    lo, hi = verdict.domain
    state = "within" if verdict.ok else "OUTSIDE"
    return (
        f"    measured on a Blackhole card with tt-metal 0.63, the [v06] spelling, x in [{lo:g}, {hi:g}]: "
        f"max rel error {verdict.rel:.3g}, max abs error {verdict.abs:.3g} ({state} the row's bound "
        f"{TOLERANCE[dtype]:g} rel; {verdict.source})"
    )


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
    by_key = {(r.op, r.unit): r for r in rows()}
    found = [
        Verdict(**json.loads(line.split(" ", 1)[1]))
        for line in done.stdout.splitlines()
        if line.startswith("TENSIX-VERDICT ")
    ]
    found = [dataclasses.replace(v, digest=digest(by_key[v.op, v.unit], v.dtype)) for v in found]
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
        fields = {"op": v.op, "dtype": v.dtype, "unit": v.unit, "ok": v.ok, "rel": v.rel, "error": v.error or None,
                  "digest": v.digest or None}  # fmt: skip
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
