# Copyright 2026 ETH Zurich and the Alloy authors.
"""The candidate space for one region, swept one factor at a time from the matrix's defaults."""

import ctypes.util
from dataclasses import dataclass, field

from alloy.configuration_matrix import Matrix
from alloy.regions import Region


@dataclass(slots=True, frozen=True)
class Candidate:
    """One rendering + build of a region, as names into the matrix. ``knobs`` holds only non-default values;
    an empty ``index_width`` / ``fp_level`` means the matrix default."""

    language: str
    compiler: str
    knobs: tuple[tuple[str, str], ...] = ()
    index_width: str = ""
    fp_level: str = ""
    veclib: str = "none"
    note: str = field(default="default", compare=False)

    def resolved(self, matrix: Matrix) -> tuple[str, str]:
        """``(index_width, fp_level)`` with the defaults filled in."""
        return self.index_width or matrix.default_index_width, self.fp_level or matrix.reference_fp_level

    def name(self, matrix: Matrix) -> str:
        width, level = self.resolved(matrix)
        parts = [self.language.replace("+", "p"), self.compiler, width, level, self.veclib]
        return "_".join(parts + [f"{k}-{v}" for k, v in self.knobs])

    def codegen_params(self, matrix: Matrix) -> dict[str, str]:
        """Every readable-codegen knob this candidate renders with."""
        params = {knob: values[0] for knob, values in matrix.knobs.items()}
        params.update(dict(self.knobs))
        params.update(matrix.index_widths[self.resolved(matrix)[0]])
        return params

    def flags(self, matrix: Matrix) -> tuple[str, ...]:
        level = matrix.fp_levels[self.resolved(matrix)[1]]
        veclib = matrix.compilers[self.compiler].veclib_flags[self.veclib] if self.veclib != "none" else ()
        return (matrix.languages[self.language].std_flag, *matrix.base_flags, *level.flags, *veclib)


def available_veclibs(matrix: Matrix, compiler: str) -> tuple[str, ...]:
    """Vector math libraries ``compiler`` has flags for and this machine can link."""
    offered = matrix.compilers[compiler].veclib_flags
    return tuple(lib for lib in offered if ctypes.util.find_library(matrix.veclib_probes[lib]))


def fp_levels(matrix: Matrix, region: Region) -> tuple[str, ...]:
    """FP levels worth sweeping for ``region``: a level that needs a reduction is skipped where nothing reduces."""
    return tuple(name for name, level in matrix.fp_levels.items() if region.has_reduction or not level.need_reduction)


def flips(matrix: Matrix, region: Region, language: str, compiler: str) -> list[Candidate]:
    """The default for one language and compiler, then every single-factor change of it."""
    out = [Candidate(language, compiler)]
    for knob, values in matrix.knobs.items():
        out += [Candidate(language, compiler, knobs=((knob, v),), note=f"{knob}={v}") for v in values[1:]]
    widths = list(matrix.index_widths)[1:]
    out += [Candidate(language, compiler, index_width=w, note=f"index width {w}") for w in widths]
    out += [Candidate(language, compiler, fp_level=lv, note=f"fp {lv}") for lv in fp_levels(matrix, region)[1:]]
    if region.calls_libm:
        level = matrix.veclib_fp_level
        out += [
            Candidate(language, compiler, fp_level=level, veclib=lib, note=f"veclib {lib}")
            for lib in available_veclibs(matrix, compiler)
        ]
    return out


def one_factor_at_a_time(matrix: Matrix, region: Region) -> list[Candidate]:
    """:func:`flips` for every language and compiler in the matrix."""
    return [c for lang in matrix.languages for comp in matrix.compilers for c in flips(matrix, region, lang, comp)]
