# Copyright 2026 ETH Zurich and the Alloy authors.
"""Typed view of ``configuration_matrix.toml``: :func:`load` parses the file and refuses unknown, missing or
inconsistent entries."""

import pathlib
import shutil
import tomllib
from dataclasses import dataclass
from typing import Any

#: The matrix shipped with the package.
DEFAULT_PATH = pathlib.Path(__file__).resolve().parent / "configuration_matrix.toml"
SCHEMA = 1
#: Region properties an FP level may require, and the comparisons a level can be verified with.
NEEDS = frozenset({"reduction", "finite_inputs"})
TOLERANCES = frozenset({"exact", "band"})


@dataclass(slots=True, frozen=True)
class Defaults:
    fp_level: str
    index_width: str
    cost_model: str
    openmp_runtime: str


@dataclass(slots=True, frozen=True)
class Language:
    render: str
    std: str
    suffix: str


@dataclass(slots=True, frozen=True)
class FPLevel:
    tolerance: str
    needs: str = ""


@dataclass(slots=True, frozen=True)
class Veclib:
    probe: str
    fp_level: str


@dataclass(slots=True, frozen=True)
class Compiler:
    """How one compiler spells every option; a runtime, cost model or vector library it does not list is
    unsupported."""

    executables: dict[str, str]
    remarks: tuple[str, ...]
    openmp: dict[str, tuple[str, ...]]
    fp: dict[str, tuple[str, ...]]
    cost_model: dict[str, tuple[str, ...]]
    veclib: dict[str, tuple[str, ...]]

    def missing_executables(self) -> list[str]:
        return [exe for exe in self.executables.values() if shutil.which(exe) is None]


@dataclass(slots=True, frozen=True)
class Matrix:
    path: pathlib.Path
    defaults: Defaults
    build_flags: tuple[str, ...]
    libm_calls: frozenset[str]
    languages: dict[str, Language]
    openmp_runtimes: dict[str, str]  # runtime -> soname
    fp_levels: dict[str, FPLevel]
    veclibs: dict[str, Veclib]
    compilers: dict[str, Compiler]
    knobs: dict[str, tuple[str, ...]]
    index_widths: dict[str, dict[str, str]]

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


def table(raw: dict[str, Any], where: str, required: set[str], optional: frozenset[str] = frozenset()) -> dict:
    """``raw`` after checking it names every key in ``required`` and nothing beyond ``required | optional``."""
    missing, unknown = required - raw.keys(), raw.keys() - required - optional
    if missing or unknown:
        raise ValueError(f"{where}: missing {sorted(missing)}, unknown {sorted(unknown)}")
    return raw


def flag_table(raw: dict[str, Any], where: str, allowed: set[str], *, complete: bool = False) -> dict:
    """``{option: flags}`` whose options are all in ``allowed`` (all of them when ``complete``)."""
    table(raw, where, allowed if complete else set(), frozenset(allowed))
    return {option: tuple(flags) for option, flags in raw.items()}


def compiler(raw: dict[str, Any], name: str, m: dict[str, Any]) -> Compiler:
    where = f"compilers.{name}"
    t = table(raw, where, {"remarks", "openmp", "fp"}, frozenset({*m["languages"], "cost_model", "veclib"}))
    executables = {lang: t[lang] for lang in m["languages"] if lang in t}
    if not executables:
        raise ValueError(f"{where}: names no executable for any language")
    return Compiler(
        executables=executables,
        remarks=tuple(t["remarks"]),
        openmp=flag_table(t["openmp"], f"{where}.openmp", set(m["openmp_runtimes"])),
        fp=flag_table(t["fp"], f"{where}.fp", set(m["fp_levels"]), complete=True),
        cost_model=flag_table(t.get("cost_model", {}), f"{where}.cost_model", set(m["cost_models"])),
        veclib=flag_table(t.get("veclib", {}), f"{where}.veclib", set(m["veclibs"])),
    )


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
        if d.cost_model not in comp.cost_model:
            raise ValueError(f"{m.path}: compilers.{name} does not spell the default cost model {d.cost_model!r}")
    for name, level in m.fp_levels.items():
        if level.needs and level.needs not in NEEDS:
            raise ValueError(f"{m.path}: fp_levels.{name}.needs must be one of {sorted(NEEDS)}")
        if level.tolerance not in TOLERANCES:
            raise ValueError(f"{m.path}: fp_levels.{name}.tolerance must be one of {sorted(TOLERANCES)}")
    for name, lib in m.veclibs.items():
        if lib.fp_level not in m.fp_levels:
            raise ValueError(f"{m.path}: veclibs.{name}.fp_level {lib.fp_level!r} is not declared")


def load(path: pathlib.Path = DEFAULT_PATH) -> Matrix:
    """Parse and check the matrix at ``path``."""
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    top = {
        "schema",
        "defaults",
        "build",
        "gating",
        "languages",
        "openmp_runtimes",
        "fp_levels",
        "veclibs",
        "compilers",
        "codegen",
    }
    table(raw, str(path), top)
    if raw["schema"] != SCHEMA:
        raise ValueError(f"{path}: schema {raw['schema']} is not {SCHEMA}")
    cost_models = {model for comp in raw["compilers"].values() for model in comp.get("cost_model", {})}
    names = {**raw, "cost_models": cost_models}
    codegen = table(raw["codegen"], "codegen", {"knobs", "index_widths"})
    matrix = Matrix(
        path=path,
        defaults=Defaults(**table(raw["defaults"], "defaults", set(Defaults.__slots__))),
        build_flags=tuple(table(raw["build"], "build", {"flags"})["flags"]),
        libm_calls=frozenset(table(raw["gating"], "gating", {"libm_calls"})["libm_calls"]),
        languages={
            n: Language(**table(t, f"languages.{n}", {"render", "std", "suffix"})) for n, t in raw["languages"].items()
        },
        openmp_runtimes={
            n: table(t, f"openmp_runtimes.{n}", {"soname"})["soname"] for n, t in raw["openmp_runtimes"].items()
        },
        fp_levels={
            n: FPLevel(**table(t, f"fp_levels.{n}", {"tolerance"}, frozenset({"needs"})))
            for n, t in raw["fp_levels"].items()
        },
        veclibs={n: Veclib(**table(t, f"veclibs.{n}", {"probe", "fp_level"})) for n, t in raw["veclibs"].items()},
        compilers={n: compiler(t, n, names) for n, t in raw["compilers"].items()},
        knobs={knob: tuple(values) for knob, values in codegen["knobs"].items()},
        index_widths={n: dict(t) for n, t in codegen["index_widths"].items()},
    )
    check_consistency(matrix)
    return matrix
