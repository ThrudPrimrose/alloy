# Copyright 2026 ETH Zurich and the Alloy authors.
"""Typed view of ``configuration_matrix.toml``: :func:`load` validates the file against pydantic models, which refuse
unknown or missing keys and wrong types, then checks that every cross reference names a declared entry."""

import dataclasses
import pathlib
import shutil
import tomllib
from collections.abc import Iterable
from typing import Any, Literal

from pydantic import ConfigDict, Field, TypeAdapter
from pydantic.dataclasses import dataclass

#: The matrix shipped with the package.
DEFAULT_PATH = pathlib.Path(__file__).resolve().parent / "configuration_matrix.toml"
#: Every table of the file: an unknown or a missing key is an error.
STRICT = ConfigDict(extra="forbid")


@dataclass(slots=True, frozen=True, config=STRICT)
class Defaults:
    fp_level: str
    index_width: str
    cost_model: str
    openmp_runtime: str


@dataclass(slots=True, frozen=True, config=STRICT)
class Language:
    render: str
    std: str
    suffix: str


@dataclass(slots=True, frozen=True, config=STRICT)
class FPLevel:
    """How a level is verified, and the region property it requires (none when empty)."""

    tolerance: Literal["exact", "band"]
    needs: Literal["", "reduction", "finite_inputs"] = ""


@dataclass(slots=True, frozen=True, config=STRICT)
class Veclib:
    probe: str
    fp_level: str


@dataclass(slots=True, frozen=True, config=STRICT)
class Isa:
    """A vector ISA a candidate may target, when the host lists ``host_flag`` in ``/proc/cpuinfo``."""

    host_flag: str


@dataclass(slots=True, frozen=True, config=STRICT)
class Compiler:
    """How one compiler spells every option; a runtime, cost model or vector library it does not list is
    unsupported."""

    executables: dict[str, str]
    remarks: tuple[str, ...]
    openmp: dict[str, tuple[str, ...]]
    fp: dict[str, tuple[str, ...]]
    cost_model: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    veclib: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    isa: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    support_libraries: tuple[str, ...] = ()

    def missing_executables(self) -> list[str]:
        return [exe for exe in self.executables.values() if shutil.which(exe) is None]


@dataclass(slots=True, frozen=True, config=STRICT)
class Timing:
    screen_cores: int
    screen_cache_factor: float
    final_cache_factor: float
    max_program_cache_factor: float
    screen_reps: int
    final_reps: int
    top: int


@dataclass(slots=True, frozen=True, config=STRICT)
class Build:
    flags: tuple[str, ...]


@dataclass(slots=True, frozen=True, config=STRICT)
class Gating:
    libm_calls: frozenset[str]


@dataclass(slots=True, frozen=True, config=STRICT)
class OpenMPRuntime:
    soname: str


@dataclass(slots=True, frozen=True, config=STRICT)
class Codegen:
    knobs: dict[str, tuple[str, ...]]
    index_widths: dict[str, dict[str, str]]


@dataclass(slots=True, frozen=True, config=STRICT)
class MatrixFile:
    """The file as written; a compiler's per-language executables are gathered under ``executables`` first."""

    schema: Literal[1]
    defaults: Defaults
    build: Build
    gating: Gating
    languages: dict[str, Language]
    openmp_runtimes: dict[str, OpenMPRuntime]
    fp_levels: dict[str, FPLevel]
    veclibs: dict[str, Veclib]
    isas: dict[str, Isa]
    compilers: dict[str, Compiler]
    codegen: Codegen
    timing: Timing


@dataclasses.dataclass(slots=True, frozen=True)
class Matrix:
    path: pathlib.Path
    defaults: Defaults
    build_flags: tuple[str, ...]
    libm_calls: frozenset[str]
    languages: dict[str, Language]
    openmp_runtimes: dict[str, str]  # runtime -> soname
    fp_levels: dict[str, FPLevel]
    veclibs: dict[str, Veclib]
    isas: dict[str, Isa]
    compilers: dict[str, Compiler]
    knobs: dict[str, tuple[str, ...]]
    index_widths: dict[str, dict[str, str]]
    timing: Timing

    def host_isas(self, cpu_flags: frozenset[str]) -> tuple[str, ...]:
        """The declared ISAs a host with ``cpu_flags`` (:func:`alloy.machine.cpu_flags`) can run."""
        return tuple(name for name, isa in self.isas.items() if isa.host_flag in cpu_flags)

    def usable_compilers(self) -> tuple[dict[str, Compiler], dict[str, str]]:
        """``(usable, skipped)``: compilers whose executables are on PATH and that spell the default runtime, and
        the reason each other compiler is skipped."""
        usable, skipped = {}, {}
        runtime = self.defaults.openmp_runtime
        for name, comp in self.compilers.items():
            if missing := comp.missing_executables():
                skipped[name] = f"not on PATH: {', '.join(missing)}"
            elif runtime not in comp.openmp:
                skipped[name] = f"no flags for the {runtime} OpenMP runtime"
            else:
                usable[name] = comp
        return usable, skipped


def unknown_options(
    compiler: str, option: str, spelled: dict[str, tuple[str, ...]], known: Iterable[str], *, complete: bool
) -> str | None:
    """Why ``compilers.<compiler>.<option>`` names an undeclared entry (or, when ``complete``, misses one)."""
    missing = sorted(set(known) - spelled.keys()) if complete else []
    unknown = sorted(spelled.keys() - set(known))
    if missing or unknown:
        return f"compilers.{compiler}.{option}: missing {missing}, unknown {unknown}"
    return None


def check_consistency(m: Matrix) -> None:
    """Defaults, gating names and vector-library levels must refer to declared entries."""
    d = m.defaults
    for kind, value, known in (
        ("fp_level", d.fp_level, m.fp_levels),
        ("index_width", d.index_width, m.index_widths),
        ("openmp_runtime", d.openmp_runtime, m.openmp_runtimes),
    ):
        if value not in known:
            raise ValueError(f"{m.path}: defaults.{kind} {value!r} is not declared")
    for name, comp in m.compilers.items():
        if not comp.executables:
            raise ValueError(f"{m.path}: compilers.{name} names no executable for any language")
        options: tuple[tuple[str, dict[str, tuple[str, ...]], Iterable[str], bool], ...] = (
            ("openmp", comp.openmp, m.openmp_runtimes, False),
            ("fp", comp.fp, m.fp_levels, True),
            ("veclib", comp.veclib, m.veclibs, False),
            ("isa", comp.isa, m.isas, False),
        )
        for option, spelled, declared, complete in options:
            if reason := unknown_options(name, option, spelled, declared, complete=complete):
                raise ValueError(f"{m.path}: {reason}")
        if d.cost_model not in comp.cost_model:
            raise ValueError(f"{m.path}: compilers.{name} does not spell the default cost model {d.cost_model!r}")
    for name, lib in m.veclibs.items():
        if lib.fp_level not in m.fp_levels:
            raise ValueError(f"{m.path}: veclibs.{name}.fp_level {lib.fp_level!r} is not declared")


def gathered(raw: dict[str, Any]) -> dict[str, Any]:
    """``raw`` with each compiler's per-language executable keys moved under ``executables``."""
    languages = raw.get("languages", {})
    compilers = {
        name: {
            **{k: v for k, v in table.items() if k not in languages},
            "executables": {k: v for k, v in table.items() if k in languages},
        }
        for name, table in raw.get("compilers", {}).items()
    }
    return {**raw, "compilers": compilers}


def load(path: pathlib.Path = DEFAULT_PATH) -> Matrix:
    """Parse and check the matrix at ``path``."""
    with path.open("rb") as fh:
        f = TypeAdapter(MatrixFile).validate_python(gathered(tomllib.load(fh)))
    matrix = Matrix(
        path=path,
        defaults=f.defaults,
        build_flags=f.build.flags,
        libm_calls=f.gating.libm_calls,
        languages=f.languages,
        openmp_runtimes={n: r.soname for n, r in f.openmp_runtimes.items()},
        fp_levels=f.fp_levels,
        veclibs=f.veclibs,
        isas=f.isas,
        compilers=f.compilers,
        knobs=f.codegen.knobs,
        index_widths=f.codegen.index_widths,
        timing=f.timing,
    )
    check_consistency(matrix)
    return matrix
