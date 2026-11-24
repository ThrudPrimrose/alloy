# Copyright 2026 ETH Zurich and the Alloy authors.
"""What a table row's instruction costs on the CPUs the paper's machines carry, as llvm-mca models them: µops,
latency and reciprocal throughput per instruction (``costs.toml``, written by ``helpers/isacost.py``).

A row's cost is its compiled instruction, not its intrinsic: on Zen 4 a 512-bit ``vaddpd`` issues as two 256-bit
halves, so its reciprocal throughput is twice the 256-bit one, which no intrinsic name says."""

import functools
import pathlib
import tomllib

from pydantic import ConfigDict
from pydantic.dataclasses import dataclass

__all__ = ["CPUS", "Cost", "DEFAULT_PATH", "costs", "load"]

DEFAULT_PATH = pathlib.Path(__file__).parent / "costs.toml"

#: The CPU llvm-mca models for an ISA: Zen 4 (beverin's MI300A host) for x86, Neoverse V2 (GH200's Grace) for Arm,
#: SiFive X280 (RVV 1.0, VLEN 512) for RISC-V: no evaluated machine has RVV, and X280 is LLVM's in-order RVV model.
CPUS = {"avx2": "znver4", "avx512": "znver4", "neon": "neoverse-v2", "sve": "neoverse-v2", "rvv": "sifive-x280"}


@dataclass(frozen=True, slots=True, config=ConfigDict(extra="forbid"))
class Cost:
    """One instruction of a row as compiled for ``cpu``; ``rthroughput`` is cycles per instruction in a stream. A
    ``note`` says why the numbers are no model (they are then 0)."""

    cpu: str
    instruction: str
    uops: int
    latency: int
    rthroughput: float
    note: str = ""


@functools.lru_cache(maxsize=None, typed=True)
def load(path: pathlib.Path = DEFAULT_PATH) -> dict[str, tuple[Cost, ...]]:
    """``"isa/dtype/op"`` -> its instructions' costs; empty when the file is absent."""
    if not path.is_file():
        return {}
    raw = tomllib.loads(path.read_text())
    return {key: tuple(Cost(**row) for row in rows) for key, rows in raw.get("rows", {}).items()}


def costs(isa: str, op: str, dtype: str) -> tuple[Cost, ...]:
    """The instructions of row ``isa/dtype/op`` with their modelled cost, or ``()`` when none was measured."""
    return load().get(f"{isa}/{dtype}/{op}", ())
