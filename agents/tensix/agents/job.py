"""Turns AGENT-VERDICT lines into exit codes, since the check run shows only those (the full log is behind a login).

job.py run [DIR..]  # each folder of submissions, probes and stock (or of the DIRs named) in its own host.py
                    # process; always exit 0; prints every verdict
job.py passed       # prints a one-line summary; exit 0, 1 when a reference/ solution is wrong or failed, 199 when
                    # there are no verdicts (stock and submission verdicts are measurements, not gates)
job.py code NAME    # 0 correct, 1 wrong result, 2 build or runtime error, 3 no verdict
job.py ms NAME      # median device time in ms (capped at 254) of a correct submission, 255 otherwise
"""

import json
import os
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).parent
VERDICTS = HERE / "verdicts.json"
sys.path.insert(0, str(HERE.parent / "rows"))
from job import sfpi

#: Lines that state why a native crash happened; an abort's last lines are only the backtrace's frame.
CAUSE = ("TT_THROW", "TT_FATAL", "TT_ASSERT", "error:", "what()", "Error", "Exception", "Assertion", "terminate called")


def cause(text: str) -> list[str]:
    """The first three distinct lines of ``text`` that state a crash's cause."""
    lines = [x.strip() for x in text.splitlines() if any(k in x for k in CAUSE) and "End of error message" not in x]
    return list(dict.fromkeys(lines))[:3]


FOLDERS = ("submissions", "probes", "stock", "reference", "generated")


def label(folder: pathlib.Path) -> str:
    """A verdict's name: the folder's, prefixed by stock/ or reference/ (their folders share the task's name)."""
    return (
        f"{folder.parent.name}/{folder.name}"
        if folder.parent.name in ("stock", "reference", "generated")
        else folder.name
    )


def run(dirs: tuple[str, ...] = FOLDERS) -> int:
    """One process per submission, so a native crash or a hang costs one verdict; always exits 0 (the next steps read
    verdicts.json), and prints every verdict for the log."""
    env = {k: v for k, v in os.environ.items() if k not in ("TT_METAL_HOME", "PYTHONPATH", "LD_LIBRARY_PATH")}
    sfpi(env)
    found = []
    for folder in sorted(p for d in dirs if (HERE / d).is_dir() for p in (HERE / d).iterdir() if p.is_dir()):
        try:
            done = subprocess.run(
                [sys.executable, "host.py", f"{folder.parent.name}/{folder.name}"],
                cwd=HERE,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=300,
            )
            lines = [x for x in done.stdout.splitlines() if x.startswith("AGENT-VERDICT ")]
            if lines:
                found.append(json.loads(lines[-1].split(" ", 1)[1]))
            else:
                text = (done.stderr or "") + (done.stdout or "")
                record = folder / "RUN.json"  # a native crash leaves no host verdict: keep the run record (F14)
                found.append(
                    {
                        "name": label(folder),
                        "ok": False,
                        "err": None,
                        "ms": None,
                        "run": json.loads(record.read_text()) if record.exists() else None,
                        "error": f"crash rc={done.returncode}: " + "\n".join(cause(text)) + "\n" + text[-1200:],
                    }
                )
        except subprocess.TimeoutExpired:
            found.append(
                {
                    "name": label(folder),
                    "ok": False,
                    "err": None,
                    "ms": None,
                    "error": "timeout after 300 s (device hang?)",
                }
            )
        if not found[-1]["ok"] and "crash" in found[-1].get("error", "") + "timeout":
            subprocess.run(
                ["bash", "-c", "command -v tt-smi && tt-smi -r 0"], check=False, capture_output=True, timeout=120
            )
        v = found[-1]
        print("AGENT-VERDICT", json.dumps(v)[:2500], flush=True)
    VERDICTS.write_text(json.dumps(found))
    print("PASSED", sum(1 for v in found if v["ok"]), "of", len(found), flush=True)
    return 0


def verdict(name: str) -> dict | None:
    if not VERDICTS.exists():
        return None
    return next((v for v in json.loads(VERDICTS.read_text()) if v["name"] == name), None)


def short(v: dict) -> str:
    """One verdict in about 90 characters: name, then ok and time, wrong and error, or the first error line."""
    head = v["name"].replace("fuse_diamond", "fd").replace("tsvc_2_s451", "s451").replace("transc_log_wide", "log")
    head = head.replace("-sonnet-", "-S").replace("-haiku-", "-H").replace("lookup", "L").replace("none", "N")
    where = ""
    if "worst" in v:
        x, got, want = v["worst"]
        where = f" abs={v['abs']:.3g} worst x={x:.6g} got={got:.7g} want={want:.7g}"
    if v["name"].startswith("probe_") and "bins" in v:  # x range: max abs, max rel per bin
        where += " bins " + " ".join(f"[{lo:g},{hi:g}]:{a:.2g}/{r:.2g}" for lo, hi, a, r in v["bins"])
    if v["ok"]:
        return f"{head}:ok {v.get('ms'):.3g}ms{where if head.startswith('probe_') else ''}"
    if not v.get("error"):
        return f"{head}:wrong{where}"
    found = cause(v["error"])
    return f"{head}:{' / '.join(x[:160] for x in found) if found else v['error'].splitlines()[0][:160]}"


def main() -> int:
    if sys.argv[1] == "run":
        return run(tuple(sys.argv[2:]) or FOLDERS)
    if sys.argv[1] == "passed":
        found = json.loads(VERDICTS.read_text()) if VERDICTS.exists() else []
        summary = " | ".join(short(v) for v in found)
        print(summary, flush=True)
        print(summary, file=sys.stderr, flush=True)
        if not found:
            return 199
        return 1 if any(v["name"].startswith("reference/") and not v["ok"] for v in found) else 0
    v = verdict(sys.argv[2])
    if sys.argv[1] == "code":
        if v is None:
            return 3
        return 0 if v["ok"] else (2 if v.get("error") else 1)
    if v is None or not v["ok"] or v.get("ms") is None:
        return 255
    return min(254, int(round(v["ms"])))


if __name__ == "__main__":
    sys.exit(main())
