# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Alloy tools on the agent side: each a thin ``POST /alloy/<mode>`` (Alloy and DaCe live in the judge)."""

import json
import os
from collections.abc import Callable
from typing import Any, Literal

import pydantic
from hpcagent_agent.tools import http_json
from hpcagent_agent.tools.registry import Hints, Spec, tool


class NoArgs(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")


#: Mode -> what the tool tells the model.
MODES = {
    "profile": "Alloy's C/C++ renderings of this kernel, every candidate verified and timed; each scope's fastest "
    "whose timing clearly beats the default build, else the default. Answers with the folder of sources and a "
    "Makefile (run `make` to build the library, then submit it), each scope's compiler and flags, and the paths of "
    "the ranked report and of the advice for scopes Alloy left short.",
    "speculative": "Alloy's C/C++ renderings of this kernel, each scope's predicted best candidate (verified, not "
    "timed). Answers with the folder of sources and a Makefile (run `make` to build the library, then submit it), "
    "each scope's compiler and flags, and the paths of the ranked report and of the advice for scopes Alloy left "
    "short.",
    "reference": "The kernel's default C/C++ from DaCe, split into one translation unit per scope at the compiler's "
    "defaults, nothing swept: the starting point to edit. Answers with the folder of sources and a Makefile (run "
    "`make` to build the library, then submit it) and each scope's compiler and flags.",
}
#: Appended on a HIP task, where either mode answers with the GPU form.
GPU_NOTE = (
    " On a HIP task: the kernel's HIP host and device sources with each device map at the threadblock its compiler "
    "report ranks first, to submit as a source pair, and the path of the ranked shapes per map."
)


class IsaArgs(pydantic.BaseModel):
    """One ``python -m alloy.isa`` query, run in the judge where the table and a compiler live."""

    model_config = pydantic.ConfigDict(extra="forbid")

    command: Literal[
        "lookup",
        "reverse",
        "assist",
        "kernel",
        "tiers",
        "time",
        "schedule",
        "skeleton",
        "ops",
        "isas",
        "host",
        "tile",
        "ask",
        "ask-all",
    ]
    arguments: list[str] = pydantic.Field(
        default_factory=list, description='e.g. ["avx512", "sin", "f64"] for kernel, ["vfmadd231pd"] for reverse'
    )


ISA = (
    "The intrinsics reference: `kernel` returns sin, exp, log, pow, fmod and more as C intrinsics at strict, relaxed "
    "and fast levels; `tiers` lists a function's polynomial depths with their error, for picking one; `time` "
    "measures what an element costs here with each kernel and library call; `lookup` spells "
    "an op for an ISA and dtype; `reverse` names what an intrinsic, a mnemonic or a pasted disassembly line computes; "
    "`skeleton` gives a loop in a legal schedule; `host` says which ISAs this machine runs. `ask` answers one "
    'operation on logical data for any target (CPU, sm90, gfx942, gfx90a, tensix), e.g. ["avx512", "reduce_add", '
    '"--x", "vector:f32:96"]: feasible with its steps, or refused with the block the target takes, the nearest '
    "requests, and a fix; `ask-all` combines requests into one kernel. `lookup`, `kernel` and "
    "`skeleton` answers carry their check: `run` names where it ran (this machine, a recorded GPU run, or ttsim), "
    "`compiled` means built and not run, and `unverified` neither."
)


#: Seconds a sweep may take: minutes per scope, far past the bound on a plain judge route.
SWEEP_TIMEOUT_S = 4 * 3600

#: Both modes write a fresh folder and library in the agent's folder and touch nothing else; a repeat gives the same.
HINTS = Hints(read_only=False, destructive=False, idempotent=True, open_world=False)


def poster(mode: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def run(payload: dict[str, Any]) -> dict[str, Any]:
        body = {
            **payload,
            "kernel": http_json.assigned_kernel(payload),
            "language": http_json.task_language(),  # hip takes Alloy's GPU path
            **http_json.identity_fields(),
            "rank": http_json.judge_rank(),
            "tokens": http_json.transcript_tokens(),
        }
        data = json.dumps(body).encode("utf-8")
        answer: dict[str, Any] = http_json.call_json(f"{http_json.judge_base()}/alloy/{mode}", data, SWEEP_TIMEOUT_S)
        return answer

    return run


for mode, description in MODES.items():
    name = f"alloy_{mode}"
    told = description + GPU_NOTE
    spec = Spec(told, NoArgs, f"- `{name}` -- {told}", HINTS)
    tool(spec=spec, core=False, name=name)(poster(mode))


#: The targets a task's ``alloy_isa`` answers for, comma-separated (a packet's env); unset: every target.
TARGETS_ENV = "ALLOY_ISA_TARGETS"
#: Commands whose first argument is the target; under a restriction the others answer only ``ops``.
TARGETED = frozenset({"lookup", "kernel", "time", "schedule", "skeleton", "tile", "ask", "ask-all"})


def outside_targets(payload: dict[str, Any], allowed: frozenset[str]) -> str:
    """Why the query leaves the task's targets, or ``""``."""
    command, arguments = payload.get("command"), payload.get("arguments") or []
    if command == "ops":
        return ""
    if command not in TARGETED:
        return f"alloy_isa: {command!r} is not offered on this task; ask about {', '.join(sorted(allowed))}"
    if not arguments or str(arguments[0]) not in allowed:
        return f"alloy_isa: this task's targets are {', '.join(sorted(allowed))}; the first argument names one"
    return ""


class SweepArgs(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    folder: str = pydantic.Field(description="the `folder` an alloy_profile answer gave, after your edits")


SWEEP = (
    "Alloy's sweep over your edits: each scopes/<symbol>.c of `folder` (the `best/` folder an alloy_profile answer "
    "gave, edited in place) is compiled with every compiler, FP level, vector library and ISA flag set Alloy tries, "
    "verified against the kernel's own rendering, and timed. Answers like alloy_profile: a new folder with each "
    "scope's fastest verified build, its Makefile, and the ranked report. Keep each scope's function signature."
)
tool(spec=Spec(SWEEP, SweepArgs, f"- `alloy_sweep` -- {SWEEP}", HINTS), core=False, name="alloy_sweep")(poster("sweep"))


def isa_query(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = frozenset(t for t in os.environ.get(TARGETS_ENV, "").split(",") if t)
    if allowed and (why := outside_targets(payload, allowed)):
        return {"ok": False, "error": why}
    answer: dict[str, Any] = http_json.post_judge("/alloy/isa", payload)
    return answer


#: A query writes nothing and a repeat gives the same answer.
ISA_HINTS = Hints(read_only=True, destructive=False, idempotent=True, open_world=False)
tool(spec=Spec(ISA, IsaArgs, f"- `alloy_isa` -- {ISA}", ISA_HINTS), core=False, name="alloy_isa")(isa_query)
