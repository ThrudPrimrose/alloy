"""The runner of the agent studies: one model, one configuration, one task of a study. A chat loop over an
OpenAI-compatible endpoint (vLLM) with file tools and the configuration's help tool; the folder it leaves is the
submission.

    python agents/run_agent.py TASK CONFIG OUT --endpoint run-<id>/endpoint.json [--study tensix|softhier]
                               [--tokens 50000000] [--output 12000000]

Studies: tensix (agents/tensix/agents: files only, no judge or compiler here; agents/job.py grades the folder on the
card) and softhier (agents/softhier: the `run` tool builds the folder's kernel.c and runs it on GVSoC with the judge's
own host, in every configuration; the episode runs where the SoftHier v1 image is, SOFTHIER_IMAGE).
CONFIG: none | tool (ask) | docs | facts (FACTS.md = python -m alloy.isa page <study>). ALLOY_REPO: the Alloy checkout
(tool, facts); DOCS_TREE: the vendor tree of `docs` (tensix: the tt-metal tree; softhier: the docs-md-softhier pages).
The key is read from the file endpoint.json names.
"""

import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
import urllib.request

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE / "tools"))
import helptool

#: Each study's folder: its SPEC.md, tasks.json and briefs/.
STUDIES = {"tensix": HERE / "tensix" / "agents", "softhier": HERE / "softhier"}
STUDY = STUDIES["tensix"]


def shared() -> dict[str, pathlib.Path]:
    """Files the agent may read besides its own folder (read-only)."""
    return {
        name: STUDY / name.removeprefix("agents/")
        for name in ("SPEC.md", "tasks.json", "agents/SPEC.md", "agents/tasks.json")
    }


def tool(name: str, description: str, **params: str) -> dict:
    props = {key: {"type": "string", "description": text} for key, text in params.items()}
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": props, "required": list(params)}}}  # fmt: skip


FILE_TOOLS = [
    tool("list_files", "The files in your folder."),
    tool("read_file", "A file of your folder, or SPEC.md / tasks.json.", path="file name"),
    tool("write_file", "Create or replace a file in your folder.", path="file name, no folders", content="full text"),
    tool("finish", "End the run: your folder is the submission.", summary="one line"),
]
HELP_TOOLS = {
    "tool": [tool("ask", "The Alloy ISA lookup: the arguments of `ask` (see the Help section).", args="arguments")],
    "docs": [
        tool("docs", "The tt-metal v0.63.0 tree: the arguments of `docs` (see the Help section).", args="arguments")
    ],
}
#: SoftHier's `docs` reads the docs-md-softhier pages, not a tt-metal tree.
SOFTHIER_DOCS = tool("docs", "The SoftHier vendor documentation (softhier-sdk README and runtime headers, RVV 1.0): the "
                     "arguments of `docs` (see the Help section).", args="arguments")  # fmt: skip
#: SoftHier's build-and-run tool, in every configuration (owner, 11-23).
RUN = tool("run", "Build kernel.c of your folder with the SoftHier SDK and run it on GVSoC with the judge's host and "
           "inputs: whether it is correct, its error, and the simulated time of your kernel.")  # fmt: skip
#: The judge's longest build plus simulation.
RUN_TIMEOUT = 4000


def run_softhier(task: str, out: pathlib.Path) -> str:
    """The judge on the folder, inside the SoftHier image: its verdict, or the build or run error."""
    image = os.environ["SOFTHIER_IMAGE"]
    argv = ["singularity", "exec", "-B", f"{out}:{out}", "-B", f"{STUDY}:{STUDY}", image, "python3",
            str(STUDY / "host.py"), "grade", task, str(out)]  # fmt: skip
    try:
        done = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        return f"error: the build and simulation ran past {RUN_TIMEOUT} s"
    return (done.stdout + done.stderr).strip()


def call(name: str, args: dict, out: pathlib.Path, task: str = "") -> tuple[str, bool]:
    """A tool call's answer and whether the run ends."""
    if name == "finish":
        return "done", True
    if name == "run" and STUDY == STUDIES["softhier"]:
        answer = helptool.capped(run_softhier(task, out))
        helptool.log("runs.log", [task], answer)
        return answer, False
    if name == "list_files":
        return "\n".join(sorted(p.name for p in out.iterdir() if p.is_file())), False
    path = args.get("path", "")
    if name == "read_file" and path in shared():
        return helptool.capped(shared()[path].read_text()), False
    if name in ("read_file", "write_file") and ("/" in path or path.startswith(".") or not path):
        return f"error: {path!r}: a plain file name in your folder", False
    if name == "read_file":
        target = out / path
        return (helptool.capped(target.read_text()) if target.is_file() else f"error: no file {path}"), False
    if name == "write_file":
        (out / path).write_text(args.get("content", ""))
        return f"wrote {path}", False
    if name in ("ask", "docs"):
        request = shlex.split(args.get("args", ""))
        answer, _ = helptool.ask(request) if name == "ask" else helptool.docs(request)
        answer = helptool.capped(answer)
        helptool.log("asks.log" if name == "ask" else "docs.log", request, answer)
        return answer, False
    return f"error: no tool {name}", False


def chat(url: str, key: str, body: dict) -> dict:
    request = urllib.request.Request(f"{url}/chat/completions", json.dumps(body).encode(),
                                     {"Content-Type": "application/json", "Authorization": f"Bearer {key}"})  # fmt: skip
    with urllib.request.urlopen(request, timeout=1800) as reply:
        return json.load(reply)


def brief(task: str, config: str, tokens: int, output: int) -> str:
    help_text = (STUDY / "briefs" / f"help-{config}.md").read_text()
    eval_tasks = {t["name"] for t in json.loads((STUDY / "tasks.json").read_text())}
    kernel = f"Eval tasks, task {task}" if task in eval_tasks else task  # dev kernels have their own SPEC section
    return ((STUDY / "briefs" / "brief.md").read_text().replace("{KERNEL}", kernel)
            .replace("{LIMITS}", f"{tokens:,} tokens in total and {output:,} output tokens, no turn limit").replace("{HELP}", help_text))  # fmt: skip


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task")
    parser.add_argument("config", choices=("none", "tool", "docs", "facts"))
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--endpoint", type=pathlib.Path, required=True)
    parser.add_argument("--study", choices=tuple(STUDIES), default="tensix")
    # The HPCAgent-Bench paper's per-run budget (owner, 11-19), so runs and tooling can be reused; no turn limit.
    parser.add_argument("--tokens", type=int, default=50_000_000)
    parser.add_argument("--output", type=int, default=12_000_000)
    args = parser.parse_args()
    global STUDY
    STUDY = STUDIES[args.study]
    endpoint = json.loads(args.endpoint.read_text())
    key = pathlib.Path(endpoint["key_file"]).expanduser().read_text().strip()
    args.out.mkdir(parents=True, exist_ok=True)
    os.environ["AGENT_SUBMISSION"] = str(args.out)
    if args.config == "facts":
        (args.out / "FACTS.md").write_text(helptool.ask(["page", args.study])[0])
    messages: list[dict] = [{"role": "user", "content": brief(args.task, args.config, args.tokens, args.output)}]
    tools = FILE_TOOLS + HELP_TOOLS.get(args.config, [])
    if args.study == "softhier":
        tools = [SOFTHIER_DOCS if t is HELP_TOOLS["docs"][0] else t for t in tools] + [RUN]
    used, out_used, turn, ended = 0, 0, 0, ""
    with (args.out / "transcript.jsonl").open("w") as log:
        while True:
            reply = chat(endpoint["url"], key, {"model": endpoint["model"], "messages": messages, "tools": tools})
            used += reply["usage"]["total_tokens"]
            out_used += reply["usage"]["completion_tokens"]
            message = reply["choices"][0]["message"]
            log.write(json.dumps({"turn": turn, "usage": reply["usage"], "message": message}) + "\n")
            messages.append({k: message[k] for k in ("role", "content", "tool_calls") if message.get(k) is not None})
            calls = message.get("tool_calls") or []
            if not calls:
                ended = "no tool call"
                break
            done = False
            for c in calls:
                answer, stop = call(
                    c["function"]["name"], json.loads(c["function"]["arguments"] or "{}"), args.out, args.task
                )
                messages.append({"role": "tool", "tool_call_id": c["id"], "content": answer})
                done = done or stop
            if done:
                ended = "finish"
                break
            if used >= args.tokens or out_used >= args.output:
                ended = "tokens"
                break
            turn += 1
    summary = {"study": args.study, "task": args.task, "config": args.config, "model": endpoint["model"], "turns": turn + 1,
               "tokens": used, "output_tokens": out_used, "ended": ended}  # fmt: skip
    (args.out / "run.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
