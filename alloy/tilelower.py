# Copyright 2026 ETH Zurich and the Alloy authors.
"""The front both tile backends share (softhiergen, tensixgen): a NumPy program's SDFG to tile nodes at the target's
tile width. Each backend then places the arrays and expands the tile nodes to its own rows; :func:`lower` is the one
entry point to both."""

import warnings
from typing import TYPE_CHECKING, Literal, overload

from dace.libraries.standard.nodes.merge_node import MergeLibraryNode
from dace.libraries.tileops.nodes import TileMaskGen
from dace.sdfg import SDFG
from dace.transformation.dataflow import MapFusionVertical, RedundantArray, RedundantSecondArray
from dace.transformation.passes.vectorization.config import VectorizeConfig
from dace.transformation.passes.vectorization.enums import ISA
from dace.transformation.passes.vectorization.vectorize_cpu_multi_dim import VectorizeCPUMultiDim

if TYPE_CHECKING:
    from alloy.tensixgen.split import Program


class Unsupported(ValueError):
    """A program or node a tile backend does not lower; the message says why. Each backend's refusal is one."""


@overload
def lower(sdfg: SDFG, target: Literal["softhier"], scalars: dict[str, float] | None = None,
          name: str | None = None) -> str: ...  # fmt: skip
@overload
def lower(sdfg: SDFG, target: Literal["tensix"], scalars: dict[str, float] | None = None,
          name: str | None = None) -> "Program": ...  # fmt: skip
def lower(sdfg: SDFG, target: Literal["softhier", "tensix"], scalars: dict[str, float] | None = None,
          name: str | None = None) -> "str | Program":  # fmt: skip
    """Lowers ``sdfg`` (all symbols specialized) in place for ``target`` and returns its generated sources: SoftHier's
    C++ unit, or Tensix's reader, compute and writer kernels (``scalars``: the values of its scalar arguments, which
    Tensix fills into tiles; ``name`` names the Tensix program, by default the SDFG's). Raises the backend's
    :class:`Unsupported` refusal when it does not take the program."""
    # The backends import this module for the front, so they are imported here, at the call
    if target == "softhier":
        from alloy.softhiergen import program

        return program.generate(sdfg)
    from alloy.tensixgen import gate

    return gate.lower(sdfg, scalars or {}, name)


def front(sdfg: SDFG, width: int | tuple[int, ...], fuse_multiply_add: bool) -> None:
    """:func:`fuse`, then :func:`vectorize` at ``width`` lanes (or per-dimension widths, innermost last): the tile nodes
    both backends expand."""
    # A specialized size becomes its value in every shape and range: the vectorizer then proves the tiles divide it,
    # where it would guard a symbol at run time outside every kernel
    sdfg.replace_dict({name: value for name, value in sdfg.constants.items() if name in sdfg.symbols})
    fuse(sdfg)
    try:
        vectorize(sdfg, width, fuse_multiply_add)
    except ValueError as error:  # a remainder tile would be masked, and no backend takes a masked tile
        raise Unsupported(f"the tile width {width} must divide every elementwise extent: {error}") from error
    # An extent below the width passes the vectorizer as one masked tile
    if any(isinstance(node, TileMaskGen) for node, _ in sdfg.all_nodes_recursive()):
        raise Unsupported(f"the tile width {width} must divide every elementwise extent: one would be a masked tile")


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


def vectorize(sdfg: SDFG, width: int | tuple[int, ...], fuse_multiply_add: bool) -> None:
    """Elementwise maps to tile maps of tile nodes, ``width`` lanes each; raises ValueError when ``width`` does not
    divide an elementwise extent (no backend takes a masked remainder tile)."""
    widths = width if isinstance(width, tuple) else (width,)
    config = VectorizeConfig(widths=widths, target_isa=ISA.SCALAR, assume_even=True,
                             fuse_multiply_add=fuse_multiply_add)  # fmt: skip
    # A program with nothing elementwise (copies, library nodes, collectives) is left untiled; DaCe warns about it
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="VectorizeMultiDim: tiled nothing", category=UserWarning)
        VectorizeCPUMultiDim(config).apply_pass(sdfg, {})
