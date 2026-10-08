# Copyright 2026 ETH Zurich and the Alloy authors.
"""Typed view of ``configuration_matrix.toml``: :func:`load` parses the file and refuses unknown or missing keys."""

import pathlib
import tomllib
from dataclasses import dataclass
from typing import Any

#: The matrix at the repository top.
DEFAULT_PATH = pathlib.Path(__file__).resolve().parent.parent / "configuration_matrix.toml"


@dataclass(slots=True, frozen=True)
class Language:
    std_flag: str
    suffix: str


@dataclass(slots=True, frozen=True)
class Compiler:
    """Executables per language, the flags that make the vectorizer report, and the flags selecting each vector
    math library this compiler can use."""

    executables: dict[str, str]
    remark_flags: tuple[str, ...]
    veclib_flags: dict[str, tuple[str, ...]]


@dataclass(slots=True, frozen=True)
class FPLevel:
    flags: tuple[str, ...]
    need_reduction: bool = False


@dataclass(slots=True, frozen=True)
class Matrix:
    """Everything the sweep enumerates. Dict order is the file's order; the first FP level, knob value and index
    width are the defaults."""

    path: pathlib.Path
    base_flags: tuple[str, ...]
    libm_calls: frozenset[str]
    veclib_fp_level: str
    languages: dict[str, Language]
    compilers: dict[str, Compiler]
    veclib_probes: dict[str, str]
    fp_levels: dict[str, FPLevel]
    knobs: dict[str, tuple[str, ...]]
    index_widths: dict[str, dict[str, str]]

    @property
    def reference_fp_level(self) -> str:
        return next(iter(self.fp_levels))

    @property
    def default_index_width(self) -> str:
        return next(iter(self.index_widths))


def checked(table: dict[str, Any], keys: set[str], optional: set[str], where: str) -> dict[str, Any]:
    """``table`` after checking it names every key in ``keys``, and nothing beyond ``keys | optional``."""
    missing, unknown = keys - table.keys(), table.keys() - keys - optional
    if missing or unknown:
        raise ValueError(f"{where}: missing {sorted(missing)}, unknown {sorted(unknown)}")
    return table


def compiler(table: dict[str, Any], name: str) -> Compiler:
    t = checked(table, {"executables", "remark_flags", "veclib_flags"}, set(), f"compilers.{name}")
    return Compiler(
        dict(t["executables"]),
        tuple(t["remark_flags"]),
        {lib: tuple(flags) for lib, flags in t["veclib_flags"].items()},
    )


def load(path: pathlib.Path = DEFAULT_PATH) -> Matrix:
    """Parse and check the matrix at ``path``."""
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    top = {
        "base_flags",
        "libm_calls",
        "veclib_fp_level",
        "languages",
        "compilers",
        "veclib_probes",
        "fp_levels",
        "knobs",
        "index_widths",
    }
    checked(raw, top, set(), str(path))
    matrix = Matrix(
        path=path,
        base_flags=tuple(raw["base_flags"]),
        libm_calls=frozenset(raw["libm_calls"]),
        veclib_fp_level=raw["veclib_fp_level"],
        languages={
            name: Language(**checked(t, {"std_flag", "suffix"}, set(), f"languages.{name}"))
            for name, t in raw["languages"].items()
        },
        compilers={name: compiler(t, name) for name, t in raw["compilers"].items()},
        veclib_probes=dict(raw["veclib_probes"]),
        fp_levels={
            name: FPLevel(
                tuple(checked(t, {"flags"}, {"need_reduction"}, f"fp_levels.{name}")["flags"]),
                bool(t.get("need_reduction", False)),
            )
            for name, t in raw["fp_levels"].items()
        },
        knobs={knob: tuple(values) for knob, values in raw["knobs"].items()},
        index_widths={name: dict(t) for name, t in raw["index_widths"].items()},
    )
    if matrix.veclib_fp_level not in matrix.fp_levels:
        raise ValueError(f"{path}: veclib_fp_level {matrix.veclib_fp_level!r} is not an fp level")
    for name, comp in matrix.compilers.items():
        if unprobed := comp.veclib_flags.keys() - matrix.veclib_probes.keys():
            raise ValueError(f"{path}: compilers.{name} names vector libraries without a probe: {sorted(unprobed)}")
        if unknown := comp.executables.keys() - matrix.languages.keys():
            raise ValueError(f"{path}: compilers.{name} has executables for unknown languages {sorted(unknown)}")
    return matrix
