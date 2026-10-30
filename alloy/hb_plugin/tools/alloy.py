# Copyright 2026 ETH Zurich and the Alloy authors.
"""The Alloy tools on the agent side: each a thin ``POST /alloy/<mode>`` (Alloy and DaCe live in the judge)."""

from collections.abc import Callable
from typing import Any, Literal

import pydantic
from hpcagent_agent.tools import http_json
from hpcagent_agent.tools.registry import Hints, Spec, tool


class NoArgs(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")


#: Mode -> what the tool tells the model.
MODES = {
    "profile": "Alloy's C/C++ renderings of this kernel, every candidate verified and timed; the fastest per scope "
    "built into a library you can submit, with the sources, a Makefile and the report of the top candidates.",
    "speculative": "Alloy's C/C++ renderings of this kernel, each scope's predicted best candidate (verified, not "
    "timed) built into a library you can submit, with the sources, a Makefile and the report of the top candidates.",
}


class IsaArgs(pydantic.BaseModel):
    """One ``python -m alloy.isa`` query, run in the judge where the table and a compiler live."""

    model_config = pydantic.ConfigDict(extra="forbid")

    command: Literal["lookup", "reverse", "assist", "kernel", "schedule", "skeleton", "ops", "isas"]
    arguments: list[str] = pydantic.Field(
        default_factory=list, description='e.g. ["avx512", "sin", "f64"] for kernel, ["vfmadd231pd"] for reverse'
    )


ISA = (
    "The intrinsics reference: `kernel` returns sin, exp, log, pow and more as C intrinsics at strict, relaxed and "
    "fast levels; `lookup` spells an op for an ISA and dtype; `reverse` names what an intrinsic or mnemonic computes; "
    "`skeleton` gives a loop in a legal schedule. Every answer is checked on this machine before it is returned."
)


#: Both modes write a fresh folder and library in the shared folder and touch nothing else; a repeat gives the same.
HINTS = Hints(read_only=False, destructive=False, idempotent=True, open_world=False)


def poster(mode: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    def run(payload: dict[str, Any]) -> dict[str, Any]:
        return http_json.post_judge(f"/alloy/{mode}", {**payload, "kernel": http_json.assigned_kernel(payload)})

    return run


for mode, description in MODES.items():
    name = f"alloy_{mode}"
    spec = Spec(description, NoArgs, f"- `{name}` -- {description}", HINTS)
    tool(spec=spec, core=False, name=name)(poster(mode))


def isa_query(payload: dict[str, Any]) -> dict[str, Any]:
    return http_json.post_judge("/alloy/isa", payload)


#: A query writes nothing and a repeat gives the same answer.
ISA_HINTS = Hints(read_only=True, destructive=False, idempotent=True, open_world=False)
tool(spec=Spec(ISA, IsaArgs, f"- `alloy_isa` -- {ISA}", ISA_HINTS), core=False, name="alloy_isa")(isa_query)
