# Copyright 2026 ETH Zurich and the Alloy authors.
"""An Alloy flavor's record of one episode, kept as the bench's plugin record (``plugin_records/alloy.json``, archived
with the grade): what each scope delivered and along which axes, and what its search built, verified and timed."""

import hashlib
import json
import pathlib
import sys
import threading
from collections.abc import Callable, Mapping

import pydantic
from hpcagent_bench.harness import plugin_records
from hpcagent_bench.harness.plugin_records import CAP_BYTES
from pydantic.dataclasses import dataclass

from alloy.backend.build import Build
from alloy.backend.candidates import Candidate
from alloy.backend.sweep import ScopeReport
from alloy.configuration_matrix import Matrix
from alloy.evaluate.verify import Verdict
from alloy.heuristics.predict import Prediction
from alloy.records import RECORD, dumped_json

__all__ = [
    "BUDGET",
    "PLAIN",
    "SCHEMA",
    "Episode",
    "EpisodeScope",
    "EpisodeSeconds",
    "Keep",
    "ScopeSearch",
    "ToolCall",
    "append_tool_call",
    "file_hash",
    "axes",
    "episode",
    "keep_episode",
    "scope_record",
]

#: The record's schema version (2: axes, counts, default and per-axis best times per scope).
SCHEMA = 2
#: Bytes of the record's data under the bench's cap, the rest left for the envelope.
BUDGET = CAP_BYTES - 1024
#: ``(chosen, note)`` of every scope when the plain program, no scope outlined, is delivered.
PLAIN = ("none", "the plain program")

#: Keeps a record of a schema version: :meth:`hpcagent_bench.harness.optimizers.FlavorOptimizer.keep_record`.
Keep = Callable[[int, pydantic.JsonValue], pathlib.Path]


@dataclass(slots=True, frozen=True, config=RECORD)
class EpisodeSeconds:
    """Wall seconds of an episode's stages: Alloy's generate, the stub timings, the final scoring, and the whole."""

    generate: float
    time_stubs: float
    score: float
    total: float


@dataclass(slots=True, frozen=True, config=RECORD)
class ScopeSearch:
    """What a scope's search did. The counts are of candidates other than the reference: built (an object, no
    duplicate), verified correct, rejected by verification, and timed as stubs. ``default_ns`` is the reference's stub
    time, ``None`` untimed; ``best_ns_by_axis[axis]`` the fastest stub among the timed builds whose ``axis`` holds the
    reference's value; ``predicted_gain`` the reference's predicted cycles over the delivered build's, ``None``
    without both predictions."""

    built: int
    verified: int
    rejected: int
    timed: int
    default_ns: float | None
    best_ns_by_axis: dict[str, float]
    predicted_gain: float | None


@dataclass(slots=True, frozen=True, config=RECORD)
class EpisodeScope:
    """A scope's reference build, the build delivered for it, the delivered candidate's note and axes (empty for the
    plain program and in a truncated record), and its search (``None`` in a truncated record)."""

    symbol: str
    reference: str
    chosen: str
    note: str
    axes: dict[str, str]
    search: ScopeSearch | None


@dataclass(slots=True, frozen=True, config=RECORD)
class Episode:
    """One episode of an Alloy flavor: its mode (``profile``, ``speculative`` or ``none``), kernel, stage seconds, the
    number of stub timings it took, and every scope's record; ``truncated`` when the searches were dropped to fit the
    bench's cap."""

    schema: int
    mode: str
    kernel: str
    seconds: EpisodeSeconds
    stubs: int
    scopes: tuple[EpisodeScope, ...]
    truncated: bool


def axes(candidate: Candidate, matrix: Matrix) -> dict[str, str]:
    """Every axis of ``candidate`` resolved to its value, defaults named: what E2 compares without parsing a name."""
    level, model = candidate.resolved(matrix)
    return {
        "language": candidate.language,
        "compiler": candidate.compiler,
        "fp_level": level,
        "cost_model": model,
        "veclib": candidate.veclib,
        "isa": candidate.isa or "native",
        "tail": candidate.tail or "compiler",
        "fission": "cut" if candidate.fission else "whole",
        "threading": "serial" if candidate.serial else "parallel",
        "approx": candidate.approx or "library",
        "knobs": ",".join(f"{k}-{v}" for k, v in candidate.knobs) or "default",
    }


def best_by_axis(
    reference: dict[str, str], timed: Mapping[str, float], axes_of: Mapping[str, dict[str, str]]
) -> dict[str, float]:
    """Per axis, the fastest of ``timed`` among the builds whose axis holds ``reference``'s value."""
    best: dict[str, float] = {}
    for name, ns in timed.items():
        for axis, value in axes_of[name].items():
            if value == reference[axis] and ns < best.get(axis, float("inf")):
                best[axis] = ns
    return best


def predicted_gain(
    predicted: Mapping[str, Prediction] | None, reference: Build, delivered: Build | None
) -> float | None:
    if predicted is None or delivered is None or reference.name not in predicted or delivered.name not in predicted:
        return None
    return predicted[reference.name].cycles_per_element / predicted[delivered.name].cycles_per_element


def scope_record(
    rep: ScopeReport,
    matrix: Matrix,
    delivered: Build | None,
    verdicts: Mapping[str, Verdict],
    timed: Mapping[str, float],
    predicted: Mapping[str, Prediction] | None = None,
) -> EpisodeScope:
    """The record of ``rep``'s scope: ``delivered`` its build (``None``: the plain program), ``verdicts`` and ``timed``
    (stub ns) by build name, ``predicted`` its predictions in speculative mode."""
    reference = rep.builds[0]
    distinct = [build for build in rep.builds[1:] if build.archive is not None and not build.duplicate_of]
    axes_of = {build.name: axes(build.candidate, matrix) for build in rep.builds}
    stubs = {name: ns for name, ns in timed.items() if name in axes_of}
    search = ScopeSearch(
        built=len(distinct),
        verified=sum(verdicts[b.name].ok for b in distinct if b.name in verdicts),
        rejected=sum(not verdicts[b.name].ok for b in distinct if b.name in verdicts),
        timed=sum(name != reference.name for name in stubs),
        default_ns=stubs.get(reference.name),
        best_ns_by_axis=best_by_axis(axes_of[reference.name], stubs, axes_of),
        predicted_gain=predicted_gain(predicted, reference, delivered),
    )
    chosen, note = PLAIN if delivered is None else (delivered.name, delivered.candidate.note)
    delivered_axes = {} if delivered is None else axes(delivered.candidate, matrix)
    return EpisodeScope(rep.scope.symbol, reference.name, chosen, note, delivered_axes, search)


def episode(
    mode: str, kernel: str, seconds: EpisodeSeconds, stubs: int, scopes: tuple[EpisodeScope, ...]
) -> pydantic.JsonValue:
    """The episode's record as plain JSON, every scope's axes and search dropped (and ``truncated`` set) when it would
    exceed :data:`BUDGET`; every scope's delivered build stays."""
    data = plain_json(Episode(SCHEMA, mode, kernel, seconds, stubs, scopes, truncated=False))
    if len(json.dumps(data, separators=(",", ":")).encode()) > BUDGET:
        bare = tuple(EpisodeScope(s.symbol, s.reference, s.chosen, s.note, {}, None) for s in scopes)
        data = plain_json(Episode(SCHEMA, mode, kernel, seconds, stubs, bare, truncated=True))
    return data


def plain_json(record: Episode) -> pydantic.JsonValue:
    return json.loads(dumped_json(record))


def keep_episode(keep: Keep, data: pydantic.JsonValue) -> None:
    """Keep ``data`` as the episode's plugin record; a tuner outside a bench run (no episode folder) logs and goes
    on."""
    try:
        keep(SCHEMA, data)
    except ValueError as exc:
        print(f"alloy: episode record not kept: {exc}", file=sys.stderr, flush=True)


#: The plugin whose record an Alloy tool appends to.
PLUGIN = "alloy"


@dataclass(slots=True, frozen=True, config=RECORD)
class ToolCall:
    """One call of an Alloy tool in an agent's episode: the tool, its arguments (never source text), its wall
    seconds, whether it answered, and the SHA-256 of the library and of every source unit it returned (empty for a
    query), so an analysis can tell Alloy's result from the agent's own submission."""

    tool: str
    arguments: dict[str, str]
    seconds: float
    ok: bool
    library_sha256: str
    unit_sha256: dict[str, str]


def file_hash(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


#: One lock per episode folder: the judge serves an episode's tool calls on threads of one process.
LOCKS: dict[pathlib.Path, threading.Lock] = {}
LOCKS_GUARD = threading.Lock()


def append_tool_call(folder: pathlib.Path, call: ToolCall) -> None:
    """Append ``call`` to the ``tools`` list of the episode folder's Alloy record (read, appended, written whole);
    the bench archives the record with the episode's next ``/submit`` grade. A record at the bench's cap keeps its
    earlier calls and logs the one it drops."""
    with LOCKS_GUARD:
        lock = LOCKS.setdefault(folder.resolve(), threading.Lock())
    with lock:
        path = folder / plugin_records.FOLDER / f"{PLUGIN}.json"
        held = plugin_records.read(path) if path.is_file() else None
        data = held.data if held is not None and isinstance(held.data, dict) else {"schema": SCHEMA}
        tools = data.get("tools")
        calls = [*(tools if isinstance(tools, list) else []), json.loads(dumped_json(call))]
        try:
            plugin_records.keep(folder, PLUGIN, SCHEMA, {**data, "tools": calls})
        except ValueError as exc:
            print(f"alloy: tool call {call.tool} not recorded: {exc}", file=sys.stderr, flush=True)
