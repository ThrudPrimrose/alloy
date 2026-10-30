# Copyright 2026 ETH Zurich and the Alloy authors.
"""Alloy's ISA layer: the machine abstract math ISA (:data:`OPS`) and the op x dtype x ISA instruction
table that spells it (``intrinsics.toml``), both directions — ``lookup`` for writing vector code,
``reverse`` for reading a build's intrinsics or its disassembly mnemonics back into math."""

from alloy.isa.ops import OPS, AbstractOp
from alloy.isa.table import ALIASES, DTYPES, Approx, Entry, Hit, Isa, Table, isas, load, lookup, reverse

__all__ = [
    "ALIASES",
    "DTYPES",
    "OPS",
    "AbstractOp",
    "Approx",
    "Entry",
    "Hit",
    "Isa",
    "Table",
    "isas",
    "load",
    "lookup",
    "reverse",
]
