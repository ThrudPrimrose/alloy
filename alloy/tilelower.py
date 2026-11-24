# Copyright 2026 ETH Zurich and the Alloy authors.
"""The front both tile backends share (softhiergen, tensixgen): a NumPy program's SDFG to tile nodes at the target's
tile width. Each backend then places the arrays and expands the tile nodes to its own rows."""

import warnings

from dace.libraries.standard.nodes.merge_node import MergeLibraryNode
from dace.sdfg import SDFG
from dace.transformation.dataflow import MapFusionVertical, RedundantArray, RedundantSecondArray
from dace.transformation.passes.vectorization.config import VectorizeConfig
from dace.transformation.passes.vectorization.enums import ISA
from dace.transformation.passes.vectorization.vectorize_cpu_multi_dim import VectorizeCPUMultiDim


class Unsupported(ValueError):
    """A program or node a tile backend does not lower; the message says why. Each backend's refusal is one."""


def front(sdfg: SDFG, width: int, fuse_multiply_add: bool) -> None:
    """:func:`fuse`, then :func:`vectorize` at ``width`` lanes: the tile nodes both backends expand."""
    # A specialized size becomes its value in every shape and range: the vectorizer then proves the tiles divide it,
    # where it would guard a symbol at run time outside every kernel
    sdfg.replace_dict({name: value for name, value in sdfg.constants.items() if name in sdfg.symbols})
    fuse(sdfg)
    try:
        vectorize(sdfg, width, fuse_multiply_add)
    except ValueError as error:  # a remainder tile would be masked, and no backend takes a masked tile
        raise Unsupported(f"the tile width {width} must divide every elementwise extent: {error}") from error


def fuse(sdfg: SDFG) -> None:
    """``numpy.where`` becomes an elementwise map with a ternary (the vectorizer makes it a TileITE), elementwise maps
    fuse, and an in-place update (``y[:] = a * x + y``) writes y directly: folded while the map body is still a
    tasklet RedundantArray can prove elementwise, it does not become a second kernel through memory."""
    for node, state in list(sdfg.all_nodes_recursive()):
        if isinstance(node, MergeLibraryNode):
            node.implementation = "pure"
            node.expand(state)
    # The expansion's state joins its neighbors, so its map can fuse with theirs. Dead-dataflow elimination would drop
    # the copy that fills a rooted collective's output, which the collective writes on the root only
    sdfg.simplify(skip={"DeadDataflowElimination"})
    sdfg.apply_transformations_repeated(MapFusionVertical)
    sdfg.apply_transformations_repeated([RedundantArray, RedundantSecondArray])


def vectorize(sdfg: SDFG, width: int, fuse_multiply_add: bool) -> None:
    """Elementwise maps to tile maps of tile nodes, ``width`` lanes each; raises ValueError when ``width`` does not
    divide an elementwise extent (no backend takes a masked remainder tile)."""
    config = VectorizeConfig(widths=(width,), target_isa=ISA.SCALAR, assume_even=True,
                             fuse_multiply_add=fuse_multiply_add)  # fmt: skip
    # A program with nothing elementwise (copies, library nodes, collectives) is left untiled; DaCe warns about it
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="VectorizeMultiDim: tiled nothing", category=UserWarning)
        VectorizeCPUMultiDim(config).apply_pass(sdfg, {})
