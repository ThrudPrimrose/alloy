# Copyright 2026 ETH Zurich and the Alloy authors.
"""The candidate space for one region, swept one factor at a time from the default rendering."""

import ctypes.util
from dataclasses import dataclass, field

from alloy.regions import Region

#: Readable-codegen knobs and the value each one is flipped to; the first value is DaCe's default.
KNOBS: dict[str, tuple[str, str]] = {
    "loop_access_form": ("indexed", "ptr_increment"),
    "heap_ptr_restrict": ("restrict", "none"),
    "const_scalar_abi": ("by_ref", "by_value"),
    "decl_placement": ("eager", "late"),
    "scalar_init_style": ("split", "fused"),
}
#: Index width moves as one axis: int32 helpers under int64 counters cost gcc its vectorization
#: (samples/index_width), so only the matched pair is a candidate.
INDEX_WIDTHS: dict[str, dict[str, str]] = {
    "int64": {"index_ctype": "int64", "loop_index_type": "inferred"},
    "int32": {"index_ctype": "int32", "loop_index_type": "int32"},
}
FP_LEVELS: dict[str, tuple[str, ...]] = {
    "strict": ("-ffp-contract=off",),
    "contract": ("-ffp-contract=fast",),
    "noerrno": ("-ffp-contract=fast", "-fno-math-errno", "-fno-trapping-math"),
    "reassoc": (
        "-ffp-contract=fast",
        "-fno-math-errno",
        "-fno-trapping-math",
        "-fassociative-math",
        "-fno-signed-zeros",
    ),
}
LANGUAGES = ("c", "c++")
COMPILERS: dict[str, dict[str, str]] = {
    "gcc": {"c": "gcc", "c++": "g++"},
    "clang": {"c": "clang-21", "c++": "clang++-21"},
}
BASE_FLAGS = ("-O3", "-march=native", "-fopenmp", "-fPIC")


@dataclass(slots=True, frozen=True)
class Candidate:
    """One rendering + build of a region. ``knobs`` holds only the values that differ from the default."""

    language: str
    compiler: str
    knobs: tuple[tuple[str, str], ...] = ()
    index_width: str = "int64"
    fp_level: str = "strict"
    veclib: str = "none"
    note: str = field(default="default", compare=False)

    @property
    def name(self) -> str:
        parts = [self.language.replace("+", "p"), self.compiler, self.index_width, self.fp_level, self.veclib]
        parts += [f"{k}-{v}" for k, v in self.knobs]
        return "_".join(parts)

    def codegen_params(self) -> dict[str, str]:
        """Every readable-codegen knob this candidate renders with."""
        params = {knob: values[0] for knob, values in KNOBS.items()}
        params.update(dict(self.knobs))
        params.update(INDEX_WIDTHS[self.index_width])
        return params

    def flags(self) -> tuple[str, ...]:
        std = "-std=c23" if self.language == "c" else "-std=c++20"
        return (std, *BASE_FLAGS, *FP_LEVELS[self.fp_level], *veclib_flags(self.compiler, self.veclib))


def veclib_flags(compiler: str, veclib: str) -> tuple[str, ...]:
    """Compile flags selecting a vector math library; empty for ``none``."""
    if veclib == "none":
        return ()
    if compiler == "gcc":
        return ("-fopenmp-simd", "-fno-math-errno")  # glibc's libmvec through the simd declarations in math.h
    return (f"-fveclib={'libmvec' if veclib == 'libmvec' else 'SLEEF'}", "-fno-math-errno")


def available_veclibs(compiler: str) -> tuple[str, ...]:
    """Vector math libraries this machine can link for ``compiler``."""
    libs = ["libmvec"] if ctypes.util.find_library("mvec") else []
    if compiler == "clang" and ctypes.util.find_library("sleefgnuabi"):
        libs.append("sleef")
    return tuple(libs)


def fp_levels(region: Region) -> tuple[str, ...]:
    """FP levels worth sweeping: reassociation changes code only where something reduces."""
    return tuple(level for level in FP_LEVELS if level != "reassoc" or region.has_reduction)


def one_factor_at_a_time(region: Region) -> list[Candidate]:
    """Per language and compiler: the default, then each knob, the index width, each FP level and each vector
    library flipped alone. The vector library axis opens only for a region that calls libm."""
    out: list[Candidate] = []
    for language in LANGUAGES:
        for compiler in COMPILERS:
            base = Candidate(language, compiler)
            out.append(base)
            for knob, values in KNOBS.items():
                out.append(Candidate(language, compiler, knobs=((knob, values[1]),), note=f"{knob}={values[1]}"))
            out.append(Candidate(language, compiler, index_width="int32", note="index width int32"))
            for level in fp_levels(region)[1:]:
                out.append(Candidate(language, compiler, fp_level=level, note=f"fp {level}"))
            if region.calls_libm:
                for lib in available_veclibs(compiler):
                    out.append(Candidate(language, compiler, fp_level="noerrno", veclib=lib, note=f"veclib {lib}"))
    return out
