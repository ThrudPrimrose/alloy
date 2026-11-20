# Copyright 2026 ETH Zurich and the Alloy authors.
"""The SoftHier v1 architecture: the configuration of the simulator model and of the SDK header.

The values are those Alloy's checked SoftHier rows ran on (``alloy/isa/softhier.toml``, ``[target.config]``): the SDK's
``arch_spatz_check.py`` with a 2 x 2 mesh. The image's SDK carries the matching ``flex_cluster_arch.h``.
"""

from dataclasses import asdict, dataclass

#: GVSoC target of the v1 model.
TARGET = "pulp.chips.soft_hier_old.flex_cluster"


@dataclass(frozen=True, slots=True)
class Arch:
    """Field names are the attribute names of the simulator's ``FlexClusterArch``."""

    num_cluster_x: int = 2
    num_cluster_y: int = 2
    num_core_per_cluster: int = 3
    cluster_tcdm_bank_width: int = 64
    cluster_tcdm_bank_nb: int = 64
    cluster_tcdm_base: int = 0x00000000
    cluster_tcdm_size: int = 0x00100000
    cluster_tcdm_remote: int = 0x30000000
    cluster_stack_base: int = 0x10000000
    cluster_stack_size: int = 0x00020000
    cluster_zomem_base: int = 0x18000000
    cluster_zomem_size: int = 0x00020000
    cluster_reg_base: int = 0x20000000
    cluster_reg_size: int = 0x00000200
    spatz_attaced_core_list: tuple[int, ...] = (0,)
    spatz_num_vlsu_port: int = 4
    spatz_num_function_unit: int = 4
    spatz_vlsu_port_width: int = 64
    redmule_ce_height: int = 128
    redmule_ce_width: int = 32
    redmule_ce_pipe: int = 3
    redmule_elem_size: int = 2
    redmule_queue_depth: int = 1
    redmule_reg_base: int = 0x20020000
    redmule_reg_size: int = 0x00000200
    idma_outstand_txn: int = 16
    idma_outstand_burst: int = 256
    hbm_start_base: int = 0xC0000000
    hbm_node_addr_space: int = 0x04000000
    num_node_per_ctrl: int = 1
    hbm_chan_placement: tuple[int, int, int, int] = (2, 0, 0, 2)
    noc_outstanding: int = 64
    noc_link_width: int = 512
    instruction_mem_base: int = 0x80000000
    instruction_mem_size: int = 0x00010000
    soc_register_base: int = 0x90000000
    soc_register_size: int = 0x00010000
    soc_register_eoc: int = 0x90000000
    soc_register_wakeup: int = 0x90000004
    sync_base: int = 0x40000000
    sync_interleave: int = 0x00000080
    sync_special_mem: int = 0x00000040

    @property
    def num_clusters(self) -> int:
        return self.num_cluster_x * self.num_cluster_y

    def to_arch_py(self) -> str:
        """The configuration as the simulator's architecture file (``SOFTHIER_ARCH_FILE``)."""
        lines = ["class FlexClusterArch:", "", "    def __init__(self):"]
        for name, value in asdict(self).items():
            if isinstance(value, tuple):
                text = repr(list(value))
            elif "base" in name or "size" in name or "addr" in name:
                text = hex(value)
            else:
                text = repr(value)
            lines.append(f"        self.{name} = {text}")
        return "\n".join(lines) + "\n"


#: The configuration the image's SDK header was generated for.
V1 = Arch()


def node_bases() -> list[tuple[str, int]]:
    """The HBM nodes of the model in ``hbm_chan_placement`` order (west, north, east, south): one node per cluster row
    or column on an edge with channels, each with its base address."""
    nodes: list[tuple[str, int]] = []
    base = V1.hbm_start_base
    for edge, channels, count in zip(
        ("west", "north", "east", "south"),
        V1.hbm_chan_placement,
        (V1.num_cluster_y, V1.num_cluster_x, V1.num_cluster_y, V1.num_cluster_x),
        strict=True,
    ):
        if channels:
            nodes.extend((f"{edge}{node}", base + node * V1.hbm_node_addr_space) for node in range(count))
        base += count * V1.hbm_node_addr_space
    return nodes
