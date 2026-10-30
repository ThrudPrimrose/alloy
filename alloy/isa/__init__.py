# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy's ISA layer: the machine abstract math ISA (:data:`OPS`) and the op x dtype x ISA instruction
table that spells it (``intrinsics.toml``), both directions — ``lookup`` for writing vector code,
``reverse`` for reading a build's intrinsics or its disassembly mnemonics back into math."""

from alloy.isa.hints import advice, tasklet_hints
from alloy.isa.ops import OPS, AbstractOp
from alloy.isa.schedules import compiler_spelling, legal, skeleton
from alloy.isa.table import (
    ALIASES,
    DTYPES,
    Approx,
    Assist,
    AssistHit,
    Entry,
    Hit,
    Isa,
    Table,
    isas,
    load,
    lookup,
    reverse,
)
from alloy.isa.validate import Verdict, candidates_for, host_can_run, validate, validate_all, validate_tier

__all__ = [
    "ALIASES",
    "DTYPES",
    "OPS",
    "AbstractOp",
    "Approx",
    "Assist",
    "AssistHit",
    "Entry",
    "Hit",
    "Isa",
    "Table",
    "Verdict",
    "advice",
    "candidates_for",
    "compiler_spelling",
    "host_can_run",
    "isas",
    "legal",
    "load",
    "lookup",
    "reverse",
    "skeleton",
    "tasklet_hints",
    "validate",
    "validate_all",
    "validate_tier",
]
