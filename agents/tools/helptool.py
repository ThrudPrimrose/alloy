"""The two help tools of the agent study, behind one request form (fairness audit F4, F5): every request is a
command line, its answer is text capped at the same length, and both are logged to the submission folder.

    ask  ARGS...           # the Alloy ISA lookup: python -m alloy.isa ARGS (the `tool` configuration), log asks.log
    docs grep PATTERN [DIR]  # the tt-metal v0.63.0 source tree and docs (the `docs` configuration), log docs.log
    docs read PATH [FROM [TO]]
    docs ls [DIR]

ALLOY_REPO: the Alloy checkout at the frozen commit; TT_DOCS_TREE: the pinned tree (`docs fetch` builds it), or
DOCS_TREE: another vendor tree (the SoftHier study);
AGENT_SUBMISSION: the folder the log goes to (default: the working directory).
"""

import os
import pathlib
import subprocess
import sys

#: Lines of an answer, the same for both tools.
CAP = 400
#: tt-metal v0.63.0 and the tt-llk commit it pins: the version the card runs (Daisytuner container 0.63.0).
TT_METAL_TAG = "v0.63.0"
TT_LLK_COMMIT = "da2f082eba309404a2c00ca9761c11438bff5f1f"
SPARSE = ["tt_metal/include", "tt_metal/api", "tt_metal/hw", "tt_metal/programming_examples", "tt_metal/kernels",
          "docs", "METALIUM_GUIDE.md", "tech_reports"]  # fmt: skip
#: The docs tree: DOCS_TREE (the SoftHier study: the docs-md-softhier pages), else the pinned tt-metal tree.
TREE = pathlib.Path(
    os.environ.get("DOCS_TREE") or os.environ.get("TT_DOCS_TREE", pathlib.Path.home() / ".cache/tt-metal-v0.63.0")
)


def capped(text: str) -> str:
    lines = text.splitlines()
    if len(lines) <= CAP:
        return text
    return "\n".join(lines[:CAP]) + f"\n... ({len(lines) - CAP} more lines; narrow the request)"


def log(name: str, request: list[str], answer: str) -> None:
    folder = pathlib.Path(os.environ.get("AGENT_SUBMISSION", "."))
    with (folder / name).open("a") as out:
        out.write(f"=== REQUEST: {' '.join(request)}\n{answer}\n\n")


def ask(args: list[str]) -> tuple[str, int]:
    repo = os.environ["ALLOY_REPO"]
    done = subprocess.run([sys.executable, "-m", "alloy.isa", *args], cwd=repo, capture_output=True, text=True,
                          check=False, timeout=600)  # fmt: skip
    return done.stdout + done.stderr, done.returncode


def fetch() -> str:
    """The pinned tree: tt-metal at the tag and tt-llk at its commit, sparse and without history."""
    if (TREE / "tt_metal").exists():
        return f"{TREE} exists"
    run = lambda *a, cwd=None: subprocess.run(list(a), cwd=cwd, check=True, capture_output=True)
    run("git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", "--branch", TT_METAL_TAG,
        "https://github.com/tenstorrent/tt-metal", str(TREE))  # fmt: skip
    run("git", "sparse-checkout", "set", "--no-cone", *SPARSE, cwd=TREE)
    llk = TREE / "tt_metal/third_party/tt_llk"
    run("git", "init", "-q", str(llk))
    run("git", "remote", "add", "origin", "https://github.com/tenstorrent/tt-llk", cwd=llk)
    run("git", "fetch", "--depth", "1", "origin", TT_LLK_COMMIT, cwd=llk)
    run("git", "checkout", "-q", "FETCH_HEAD", cwd=llk)
    return f"{TREE}: tt-metal {TT_METAL_TAG}, tt-llk {TT_LLK_COMMIT[:7]}"


def inside(path: str) -> pathlib.Path:
    target = (TREE / path).resolve()
    if TREE.resolve() not in (target, *target.parents):
        raise ValueError(f"{path}: outside the documentation tree")
    return target


def docs(args: list[str]) -> tuple[str, int]:
    if not args or args[0] not in ("grep", "read", "ls", "fetch"):
        return "docs grep PATTERN [DIR] | docs read PATH [FROM [TO]] | docs ls [DIR]", 64
    if args[0] == "fetch":
        return fetch(), 0
    if args[0] == "grep" and len(args) in (2, 3):
        where = inside(args[2] if len(args) == 3 else ".")
        done = subprocess.run(["grep", "-rnI", "--exclude-dir=.git", "-E", "--", args[1], str(where)], capture_output=True, text=True,
                              check=False)  # fmt: skip
        return done.stdout.replace(str(TREE.resolve()) + "/", "") or "no match", 0
    if args[0] == "read" and 2 <= len(args) <= 4:
        lines = inside(args[1]).read_text(errors="replace").splitlines()
        first = int(args[2]) if len(args) > 2 else 1
        last = int(args[3]) if len(args) > 3 else len(lines)
        return "\n".join(f"{n}: {lines[n - 1]}" for n in range(max(first, 1), min(last, len(lines)) + 1)), 0
    if args[0] == "ls" and len(args) <= 2:
        where = inside(args[1] if len(args) == 2 else ".")
        return "\n".join(sorted(p.name + ("/" if p.is_dir() else "") for p in where.iterdir() if p.name != ".git")), 0
    return "docs grep PATTERN [DIR] | docs read PATH [FROM [TO]] | docs ls [DIR]", 64


def main() -> int:
    tool, args = sys.argv[1], sys.argv[2:]  # the launchers ask and docs pass their name
    try:
        answer, code = ask(args) if tool == "ask" else docs(args)
    except (ValueError, OSError) as err:  # a path outside the tree, a missing file: an answer, not a crash
        answer, code = f"error: {err}", 2
    answer = capped(answer)
    log("asks.log" if tool == "ask" else "docs.log", args, answer)
    print(answer)
    return code


if __name__ == "__main__":
    sys.exit(main())
