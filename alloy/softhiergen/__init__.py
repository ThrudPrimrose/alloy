# Copyright 2026 ETH Zurich and the Alloy authors.
"""SoftHier code generation for DaCe. Importing the package registers the storages, the schedule, the code
generation target and the SoftHier expansions of DaCe's tile, copy, sync and communication nodes."""

from alloy.softhiergen import storage
from alloy.softhiergen.codegen import target
from alloy.softhiergen.library import collectives, dma, kernels, redmule, rvv, sync

__all__ = ["collectives", "dma", "kernels", "redmule", "rvv", "storage", "sync", "target"]
