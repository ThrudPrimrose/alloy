"""Runs the Tensix rows on the device and turns the verdicts into exit codes, since the check run reports only those.

job.py run            # every row; exit 0 when the harness printed a verdict for every row, 100 + their count when for some, else died()
job.py summary        # which groups fail and how (see summary)
job.py count UNIT DT  # failures among the rows of one unit and dtype (0 = all ok, 99 = no verdicts)
"""

import json
import os
import pathlib
import subprocess
import sys
import tarfile
import urllib.request

HERE = pathlib.Path(__file__).parent
VERDICTS = HERE / "verdicts.json"
SFPI = "https://github.com/tenstorrent/sfpi/releases/download/v6.21.0/sfpi_6.21.0_x86_64.txz"


def sfpi(env: dict) -> None:
    """The wheel reads the compiler from /opt/tenstorrent/sfpi or its runtime folder; fill the latter if needed."""
    if pathlib.Path("/opt/tenstorrent/sfpi").is_dir():
        return
    subprocess.run([sys.executable, "-c", "import ttnn"], cwd=HERE, env=env, check=False, capture_output=True)
    runtime = HERE / ".ttnn_runtime_artifacts" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    if (runtime / "sfpi").exists():
        return
    tree = pathlib.Path("/tenstorrent/tt-metalium/runtime/sfpi")
    if tree.is_dir():
        (runtime / "sfpi").symlink_to(tree)
        return
    archive = HERE / "sfpi.txz"
    urllib.request.urlretrieve(SFPI, archive)
    with tarfile.open(archive) as tar:
        tar.extractall(runtime)


def run() -> int:
    env = {k: v for k, v in os.environ.items() if k not in ("TT_METAL_HOME", "PYTHONPATH", "LD_LIBRARY_PATH")}
    sfpi(env)
    done = subprocess.run(
        [sys.executable, "tensix_harness.py", "rows.json"], cwd=HERE, env=env, capture_output=True, text=True,
        check=False, timeout=1500,
    )  # fmt: skip
    found = [json.loads(x.split(" ", 1)[1]) for x in done.stdout.splitlines() if x.startswith("TENSIX-VERDICT ")]
    VERDICTS.write_text(json.dumps(found))
    for v in found:
        tail = v["rel"] if v.get("rel") is not None else v.get("error", "")[-300:]
        print(f"{v['op']:6} {v['dtype']:5} {v['unit']:5} {'ok' if v['ok'] else 'FAIL'} {tail}")
    total = len(json.loads((HERE / "rows.json").read_text()))
    print(f"== {sum(v['ok'] for v in found)} ok of {len(found)} verdicts, {total} rows, harness exit {done.returncode}")
    if len(found) < total:
        print(done.stdout[-3000:])
        print(done.stderr[-6000:])
        return died(done.returncode, done.stdout + done.stderr) if not found else 100 + len(found)
    return 0


#: What the harness's last output says about its death, most specific first.
CAUSES = ("was not declared", "has no member", "TensorAccessor", "No such file", "error:", "TT_FATAL", "TT_THROW",
          "imed out", "Traceback")  # fmt: skip


def died(code: int, output: str) -> int:
    """The exit code of a harness that gave no verdict: tens say how it ended (20 a signal other than the two
    below, 30 SIGABRT, 40 SIGSEGV, 50 a Python exception in main, 60 another exit), units the first of
    :data:`CAUSES` its output holds (1-based, 0 for none)."""
    tens = {-6: 30, -11: 40, 2: 50}.get(code, 20 if code < 0 else 60)
    return tens + next((k + 1 for k, cause in enumerate(CAUSES) if cause in output), 0)


def count(unit: str, dtype: str) -> int:
    if not VERDICTS.is_file():
        return 99
    group = [v for v in json.loads(VERDICTS.read_text()) if v["unit"] == unit and v["dtype"] == dtype]
    return sum(not v["ok"] for v in group) if group else 99


GROUPS = (("SFPU", "f32"), ("SFPU", "bf16"), ("FPU", "f32"), ("FPU", "bf16"))


def summary() -> int:
    """One byte for the whole table: bit ``k`` set when group ``k`` of :data:`GROUPS` has a failing row, plus 16
    times the class of the first failure (0 an error within 1e-2, 1 a larger one, 2 a non-finite one, 3 a Python
    API error, 4 a kernel build error, 5 another exception). 99 without verdicts."""
    if not VERDICTS.is_file():
        return 99
    failed = [v for v in json.loads(VERDICTS.read_text()) if not v["ok"]]
    if not failed:
        return 0
    bits = sum(1 << k for k, (unit, dtype) in enumerate(GROUPS) if count(unit, dtype) not in (0, 99))
    rel = failed[0].get("rel")
    error = failed[0].get("error", "")
    if rel is not None:
        kind = 2 if rel != rel or rel == float("inf") else 0 if rel <= 1e-2 else 1
    elif error.startswith(("AttributeError", "TypeError")):
        kind = 3  # the Python API differs
    else:
        kind = 4 if any(word in error for word in ("error:", "build", "compil")) else 5
    return bits + 16 * kind


def sfpu_counts() -> int:
    """16 times the failing SFPU f32 rows plus the failing SFPU bf16 rows (14 of each at most)."""
    return 16 * count("SFPU", "f32") + count("SFPU", "bf16") if VERDICTS.is_file() else 255


def failing(dtype: str, half: int) -> int:
    """A bit per failing SFPU row of ``dtype`` in table order: rows 0-6 (``half`` 0) or 7-13 (``half`` 1), plus 128
    so that no failure in the half still shows (128)."""
    group = [v for v in json.loads(VERDICTS.read_text()) if v["unit"] == "SFPU" and v["dtype"] == dtype]
    return 128 + sum(1 << k for k, v in enumerate(group[7 * half : 7 * half + 7]) if not v["ok"])


def pair(dtype: str) -> int:
    """The two failing SFPU rows of ``dtype`` as ``1 + 14 * i + j`` (table order, ``i < j``); 250 when not two."""
    group = [v for v in json.loads(VERDICTS.read_text()) if v["unit"] == "SFPU" and v["dtype"] == dtype]
    bad = [k for k, v in enumerate(group) if not v["ok"]]
    return 1 + 14 * bad[0] + bad[1] if len(bad) == 2 else 250


def magnitudes() -> int:
    """How far off the two failing SFPU f32 rows are, when they are log and tanh (else 250): ``1 + 15 * b(log) +
    b(tanh)``, ``b = floor(-2 * log10(rel))`` clamped to 0..14 (b = 4 is an error in [1e-2.5, 1e-2))."""
    import math

    group = [v for v in json.loads(VERDICTS.read_text()) if v["unit"] == "SFPU" and v["dtype"] == "f32"]
    bad = {v["op"]: v for v in group if not v["ok"]}
    if set(bad) != {"log", "tanh"} or any(v.get("rel") is None or not v["rel"] > 0 for v in bad.values()):
        return 250

    def bucket(rel: float) -> int:
        return max(0, min(14, math.floor(-2 * math.log10(rel)))) if math.isfinite(rel) else 0

    return 1 + 15 * bucket(bad["log"]["rel"]) + bucket(bad["tanh"]["rel"])


if __name__ == "__main__":
    command = sys.argv[1]
    if command == "run":
        sys.exit(run())
    if command == "summary":
        sys.exit(summary())
    if command == "sfpu":
        sys.exit(sfpu_counts())
    if command == "pair":
        sys.exit(pair(sys.argv[2]))
    if command == "magnitudes":
        sys.exit(magnitudes())
    if command == "failing":
        sys.exit(failing(sys.argv[2], int(sys.argv[3])))
    sys.exit(count(sys.argv[2], sys.argv[3]))
