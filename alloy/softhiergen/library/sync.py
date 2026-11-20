# Copyright 2026 ETH Zurich and the Alloy authors.
"""Synchronization on SoftHier: DaCe's ``Sync`` node (a thread block is a cluster, the grid the mesh) and the waits for
the two asynchronous engines, iDMA and RedMulE. Each is one call; the nodes order by empty edges."""

from typing import ClassVar

import dace
from dace import library, nodes
from dace.libraries.standard.nodes.sync import Sync, SyncScope
from dace.transformation.transformation import ExpandTransformation

from alloy.softhiergen.library.common import COMPUTE_CORE, DMA_CORE, LoweringError, side_effect_tasklet

IMPLEMENTATION = "SoftHier"

#: ``flex_intra_cluster_sync`` meets the cores of a cluster; ``flex_global_barrier_xy`` every core of the mesh.
SYNC_CODE = {SyncScope.BLOCK: "dsh_cluster_sync();", SyncScope.GRID: "dsh_global_barrier();"}


@library.register_expansion(Sync, IMPLEMENTATION)  # pyright: ignore[reportArgumentType] -- DaCe's annotation
class ExpandSyncSoftHier(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: Sync, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        if node.scope not in SYNC_CODE:
            raise LoweringError(f"{node.label}: SoftHier has cluster (BLOCK) and mesh (GRID) barriers only")
        return side_effect_tasklet(parent_state, node.label, SYNC_CODE[node.scope])


@library.expansion
class ExpandDmaWait(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: nodes.LibraryNode, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        return side_effect_tasklet(parent_state, node.label, f"if ({DMA_CORE}) dsh_dma_wait();")


@library.expansion
class ExpandRedmuleWait(ExpandTransformation):
    environments: ClassVar[list[type]] = []

    @staticmethod
    def expansion(node: nodes.LibraryNode, parent_state: dace.SDFGState, parent_sdfg: dace.SDFG) -> nodes.Tasklet:
        return side_effect_tasklet(parent_state, node.label, f"if ({COMPUTE_CORE}) dsh_redmule_wait();")


@library.node
class DmaWait(nodes.LibraryNode):
    """The DMA core waits until every transfer it issued has completed (``flex_dma_async_wait_all``)."""

    implementations: ClassVar[dict[str, type]] = {IMPLEMENTATION: ExpandDmaWait}
    default_implementation = IMPLEMENTATION

    def has_side_effects(self, sdfg: dace.SDFG) -> bool:
        return True


@library.node
class RedmuleWait(nodes.LibraryNode):
    """The compute core waits until RedMulE has finished its product (``flex_redmule_wait``)."""

    implementations: ClassVar[dict[str, type]] = {IMPLEMENTATION: ExpandRedmuleWait}
    default_implementation = IMPLEMENTATION

    def has_side_effects(self, sdfg: dace.SDFG) -> bool:
        return True
