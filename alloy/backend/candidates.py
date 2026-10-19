# Copyright 2026 ETH Zurich and the Alloy authors.
"""The candidate space for one region, swept one factor at a time from the matrix's defaults."""

import ctypes.util
from dataclasses import dataclass, field

import numpy as np

from alloy import machine
from alloy.configuration_matrix import Compiler, Matrix
from alloy.frontend.regions import Region

#: A code variant's identity: the language and every codegen knob it is rendered with.
RenderKey = tuple[str, tuple[tuple[str, str], ...]]


@dataclass(slots=True, frozen=True)
class Candidate:
    """One rendering + build of a region, as names into the matrix. ``knobs`` holds only non-default values;
    an empty ``index_width`` / ``fp_level`` / ``cost_model`` means the matrix default, an empty ``isa`` the build
    flags' ``-march=native``."""

    language: str
    compiler: str
    knobs: tuple[tuple[str, str], ...] = ()
    index_width: str = ""
    fp_level: str = ""
    cost_model: str = ""
    veclib: str = "none"
    isa: str = ""
    note: str = field(default="default", compare=False)

    def resolved(self, matrix: Matrix) -> tuple[str, str, str]:
        """``(index_width, fp_level, cost_model)`` with the defaults filled in."""
        d = matrix.defaults
        return self.index_width or d.index_width, self.fp_level or d.fp_level, self.cost_model or d.cost_model

    def tolerance(self, matrix: Matrix) -> str:
        """How this candidate's outputs are compared: its FP level's tolerance."""
        return matrix.fp_levels[self.resolved(matrix)[1]].tolerance

    def name(self, matrix: Matrix) -> str:
        width, level, model = self.resolved(matrix)
        parts = [self.language, self.compiler, width, level, model, self.veclib, *([self.isa] if self.isa else [])]
        return "_".join(parts + [f"{k}-{v}" for k, v in self.knobs])

    def variant_key(self, matrix: Matrix) -> RenderKey:
        """The code variant this candidate compiles: candidates with one key share one source."""
        return self.language, tuple(sorted(self.codegen_params(matrix).items()))

    def config_name(self, matrix: Matrix) -> str:
        """The build configuration, everything but the source: the column of the region's runtime matrix."""
        _, level, model = self.resolved(matrix)
        return "_".join([self.compiler, level, model, self.veclib, self.isa or "native"])

    def codegen_params(self, matrix: Matrix) -> dict[str, str]:
        """Every readable-codegen knob this candidate renders with."""
        params = {knob: values[0] for knob, values in matrix.knobs.items()}
        params.update(dict(self.knobs))
        params.update(matrix.index_widths[self.resolved(matrix)[0]])
        return params

    def flags(self, matrix: Matrix) -> tuple[str, ...]:
        """Compile flags: language standard, build flags, then this compiler's spelling of the default OpenMP
        runtime, the FP level, the cost model, the vector library and the ISA."""
        comp = matrix.compilers[self.compiler]
        _, level, model = self.resolved(matrix)
        veclib = comp.veclib[self.veclib] if self.veclib != "none" else ()
        isa = comp.isa[self.isa] if self.isa else ()
        return (
            matrix.languages[self.language].std,
            *matrix.build_flags,
            *comp.openmp[matrix.defaults.openmp_runtime],
            *comp.fp[level],
            *comp.cost_model[model],
            *veclib,
            *isa,
        )


def available_veclibs(matrix: Matrix, comp: Compiler) -> tuple[str, ...]:
    """Vector math libraries ``comp`` has flags for and this machine can link."""
    return tuple(lib for lib in comp.veclib if ctypes.util.find_library(matrix.veclibs[lib].probe))


def fp_levels(matrix: Matrix, region: Region, *, finite_inputs: bool) -> tuple[str, ...]:
    """FP levels whose requirement ``region`` meets: ``reduction`` needs a reducing region, ``finite_inputs`` the
    caller's declaration that no input is NaN or Inf."""
    met = {"": True, "reduction": region.has_reduction, "finite_inputs": finite_inputs}
    return tuple(name for name, level in matrix.fp_levels.items() if met[level.needs])


def index_widths(matrix: Matrix, max_elements: int | None) -> tuple[str, ...]:
    """Index widths whose type holds every flat index below ``max_elements``, the largest array's element count at
    the sizes the program runs at; every width when that is unknown (no manifest, so nothing is timed or shipped)."""
    return tuple(
        name
        for name, params in matrix.index_widths.items()
        if max_elements is None or max_elements <= np.iinfo(np.dtype(params["index_ctype"])).max
    )


def flips(
    matrix: Matrix,
    region: Region,
    language: str,
    compiler: str,
    *,
    finite_inputs: bool,
    max_elements: int | None,
    isas: tuple[str, ...] = (),
) -> list[Candidate]:
    """The default for one language and compiler, then every single-factor change of it; ``isas`` are the ISAs the
    host runs (:meth:`Matrix.host_isas`), tried where the compiler spells them."""
    comp, d = matrix.compilers[compiler], matrix.defaults
    levels = fp_levels(matrix, region, finite_inputs=finite_inputs)
    out = [Candidate(language, compiler)]
    for knob, values in matrix.knobs.items():
        out += [Candidate(language, compiler, knobs=((knob, v),), note=f"{knob}={v}") for v in values[1:]]
    out += [
        Candidate(language, compiler, index_width=w, note=f"index width {w}")
        for w in index_widths(matrix, max_elements)
        if w != d.index_width
    ]
    out += [Candidate(language, compiler, fp_level=lv, note=f"fp {lv}") for lv in levels if lv != d.fp_level]
    out += [Candidate(language, compiler, isa=i, note=f"isa {i}") for i in isas if i in comp.isa]
    out += [
        Candidate(language, compiler, cost_model=m, note=f"cost model {m}")
        for m in comp.cost_model
        if m != d.cost_model
    ]
    if region.calls_libm:
        out += [
            Candidate(language, compiler, fp_level=matrix.veclibs[lib].fp_level, veclib=lib, note=f"veclib {lib}")
            for lib in available_veclibs(matrix, comp)
            if matrix.veclibs[lib].fp_level in levels
        ]
    return out


def one_factor_at_a_time(
    matrix: Matrix, region: Region, *, finite_inputs: bool = False, max_elements: int | None = None
) -> list[Candidate]:
    """:func:`flips` for every language and every usable compiler (on PATH, spelling the default runtime)."""
    usable, _ = matrix.usable_compilers()
    isas = matrix.host_isas(machine.cpu_flags())
    return [
        c
        for lang in matrix.languages
        for comp, spec in usable.items()
        if lang in spec.executables
        for c in flips(matrix, region, lang, comp, finite_inputs=finite_inputs, max_elements=max_elements, isas=isas)
    ]
