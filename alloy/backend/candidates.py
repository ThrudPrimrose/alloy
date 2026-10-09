# Copyright 2026 ETH Zurich and the Alloy authors.
"""The candidate space for one region, swept one factor at a time from the matrix's defaults."""

import ctypes.util
from dataclasses import dataclass, field

from alloy.configuration_matrix import Compiler, Matrix
from alloy.frontend.regions import Region


@dataclass(slots=True, frozen=True)
class Candidate:
    """One rendering + build of a region, as names into the matrix. ``knobs`` holds only non-default values;
    an empty ``index_width`` / ``fp_level`` / ``cost_model`` means the matrix default."""

    language: str
    compiler: str
    knobs: tuple[tuple[str, str], ...] = ()
    index_width: str = ""
    fp_level: str = ""
    cost_model: str = ""
    veclib: str = "none"
    note: str = field(default="default", compare=False)

    def resolved(self, matrix: Matrix) -> tuple[str, str, str]:
        """``(index_width, fp_level, cost_model)`` with the defaults filled in."""
        d = matrix.defaults
        return self.index_width or d.index_width, self.fp_level or d.fp_level, self.cost_model or d.cost_model

    def name(self, matrix: Matrix) -> str:
        width, level, model = self.resolved(matrix)
        parts = [self.language, self.compiler, width, level, model, self.veclib]
        return "_".join(parts + [f"{k}-{v}" for k, v in self.knobs])

    def codegen_params(self, matrix: Matrix) -> dict[str, str]:
        """Every readable-codegen knob this candidate renders with."""
        params = {knob: values[0] for knob, values in matrix.knobs.items()}
        params.update(dict(self.knobs))
        params.update(matrix.index_widths[self.resolved(matrix)[0]])
        return params

    def flags(self, matrix: Matrix) -> tuple[str, ...]:
        """Compile flags: language standard, build flags, then this compiler's spelling of the default OpenMP
        runtime, the FP level, the cost model and the vector library."""
        comp = matrix.compilers[self.compiler]
        _, level, model = self.resolved(matrix)
        veclib = comp.veclib[self.veclib] if self.veclib != "none" else ()
        return (
            matrix.languages[self.language].std,
            *matrix.build_flags,
            *comp.openmp[matrix.defaults.openmp_runtime],
            *comp.fp[level],
            *comp.cost_model[model],
            *veclib,
        )


def available_veclibs(matrix: Matrix, comp: Compiler) -> tuple[str, ...]:
    """Vector math libraries ``comp`` has flags for and this machine can link."""
    return tuple(lib for lib in comp.veclib if ctypes.util.find_library(matrix.veclibs[lib].probe))


def fp_levels(matrix: Matrix, region: Region, *, finite_inputs: bool) -> tuple[str, ...]:
    """FP levels whose requirement ``region`` meets: ``reduction`` needs a reducing region, ``finite_inputs`` the
    caller's declaration that no input is NaN or Inf."""
    met = {"": True, "reduction": region.has_reduction, "finite_inputs": finite_inputs}
    return tuple(name for name, level in matrix.fp_levels.items() if met[level.needs])


def flips(matrix: Matrix, region: Region, language: str, compiler: str, *, finite_inputs: bool) -> list[Candidate]:
    """The default for one language and compiler, then every single-factor change of it."""
    comp, d = matrix.compilers[compiler], matrix.defaults
    out = [Candidate(language, compiler)]
    for knob, values in matrix.knobs.items():
        out += [Candidate(language, compiler, knobs=((knob, v),), note=f"{knob}={v}") for v in values[1:]]
    out += [
        Candidate(language, compiler, index_width=w, note=f"index width {w}")
        for w in matrix.index_widths
        if w != d.index_width
    ]
    out += [
        Candidate(language, compiler, fp_level=lv, note=f"fp {lv}")
        for lv in fp_levels(matrix, region, finite_inputs=finite_inputs)
        if lv != d.fp_level
    ]
    out += [
        Candidate(language, compiler, cost_model=m, note=f"cost model {m}")
        for m in comp.cost_model
        if m != d.cost_model
    ]
    if region.calls_libm:
        out += [
            Candidate(language, compiler, fp_level=matrix.veclibs[lib].fp_level, veclib=lib, note=f"veclib {lib}")
            for lib in available_veclibs(matrix, comp)
        ]
    return out


def one_factor_at_a_time(matrix: Matrix, region: Region, *, finite_inputs: bool = False) -> list[Candidate]:
    """:func:`flips` for every language and every usable compiler (on PATH, spelling the default runtime)."""
    usable, _ = matrix.usable_compilers()
    return [
        c
        for lang in matrix.languages
        for comp, spec in usable.items()
        if lang in spec.executables
        for c in flips(matrix, region, lang, comp, finite_inputs=finite_inputs)
    ]
