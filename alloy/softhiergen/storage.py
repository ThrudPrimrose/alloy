# Copyright 2026 ETH Zurich and the Alloy authors.
"""The SoftHier storages and schedule, registered into DaCe's extensible enums."""

from dace import dtypes

dtypes.StorageType.register("SoftHier_TCDM")
dtypes.StorageType.register("SoftHier_HBM")
dtypes.ScheduleType.register("SoftHier_Device")

#: Cluster SRAM. The linker places each array in ``.l1``: one address, the same on every cluster.
TCDM = dtypes.StorageType.SoftHier_TCDM  # pyright: ignore[reportAttributeAccessIssue] -- DaCe's annotation
#: Side HBM, west channel 0. The linker places each array in ``.hbm``, which the simulator preloads.
HBM = dtypes.StorageType.SoftHier_HBM  # pyright: ignore[reportAttributeAccessIssue] -- DaCe's annotation
#: A map over clusters: cluster c runs iterations c, c + P, ...; every core of the cluster runs them.
DEVICE = dtypes.ScheduleType.SoftHier_Device  # pyright: ignore[reportAttributeAccessIssue] -- DaCe's annotation

dtypes.SCOPEDEFAULT_STORAGE[DEVICE] = TCDM
dtypes.SCOPEDEFAULT_SCHEDULE[DEVICE] = dtypes.ScheduleType.Sequential
