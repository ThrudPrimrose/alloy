# Copyright 2026 ETH Zurich and the Alloy authors.
"""The approximation axis: a scope's libm calls answered by inline ladder kernels (:mod:`alloy.isa.mathkernels`) at
one rung, rendered as scalar C that the scope's own compiler vectorizes inside its loop.

A candidate of the axis is the scope's unit with :func:`prelude` in front of it: every called
function's kernel at the rung, each marked ``#pragma omp declare simd``, and a macro per libm name (``sin``,
``sinf``) that sends the unit's calls to the kernel. The prelude comes after ``<math.h>``, so the macros rename the
unit's calls and not the header's declarations."""

import re

from alloy.isa.mathkernels import functions, kernel, render

__all__ = ["LEVELS", "called_functions", "levels_for", "prelude"]

#: The rungs the matrix offers. ``strict`` keeps libm's special values on every input; ``relaxed`` holds only for
#: finite inputs in its range, so it is offered when the inputs are declared finite. Lower rungs trade digits, which
#: only a caller with a stated error bound can accept (the ISA lookup's ``--max-ulp``).
LEVELS = ("strict", "relaxed")

#: A C call of a libm name, f64 (``sin``) or f32 (``sinf``).
CALL = re.compile(r"\b([a-z][a-z0-9]*?)(f?)\s*\(")


def called_functions(source: str) -> tuple[str, ...]:
    """The ladder functions ``source`` calls, by their f64 name, in ladder order."""
    known = set(functions())
    called = {name for name, _ in CALL.findall(source) if name in known}
    return tuple(fn for fn in functions() if fn in called)


def levels_for(*, finite_inputs: bool) -> tuple[str, ...]:
    """The rungs a scope's candidates take: ``relaxed`` needs finite inputs."""
    return LEVELS if finite_inputs else LEVELS[:1]


def prelude(level: str, called: tuple[str, ...]) -> str:
    """The lines a unit at rung ``level`` starts with, for the ladder functions it calls (f64 and f32 alike)."""
    if level not in LEVELS:
        raise ValueError(f"{level!r}: the matrix offers the rungs {LEVELS}")
    kernels, macros = [], []
    for fn in called:
        for dtype, suffix in (("f64", ""), ("f32", "f")):
            k = kernel(fn, dtype, level)
            kernels += ["#pragma omp declare simd notinbranch", render(k, "scalar").source]
            macros.append(f"#define {fn}{suffix}(...) {k.name}(__VA_ARGS__)")
    head = [f"/* Alloy approximation axis: libm calls of this unit at the {level} rung (alloy.isa.approximation). */"]
    return "\n".join([*head, "#include <math.h>", "#include <stdint.h>", *kernels, *macros, ""])
