"""Array placement over the HBM nodes (``data.Array.placement``).

Node ``k`` of a placement is HBM node ``k`` of :func:`.arch.node_bases`. A placed array is one C array per node, its
share, in that node's section: node 0 is the SDK's ``.hbm`` (it starts after ``.data``), node ``k > 0`` is
``.dsh_hbm<k>`` at the node's base. Element ``idx`` lives in share ``node_of(idx)`` at element ``offset_of(idx)``.
An array without a placement stays one array in ``.hbm``.
"""

from collections.abc import Mapping
from typing import Any

import numpy
import sympy
from dace import data, placement

from alloy.softhiergen.arch import V1, node_bases
from alloy.softhiergen.library.common import LoweringError


def section(node: int) -> str:
    return ".hbm" if node == 0 else f".dsh_hbm{node}"


def share_name(name: str, node: int) -> str:
    """The C array that holds node ``node``'s share of ``name``."""
    return f"__dsh_{name}_node{node}"


def table_name(name: str) -> str:
    """The C table of the shares of ``name``, indexed by node."""
    return f"__dsh_{name}_nodes"


def placed(desc: data.Data) -> placement.Placement | None:
    return desc.placement if isinstance(desc, data.Array) else None


def value(source: object, constants: Mapping[str, Any]) -> sympy.Expr:
    expr = sympy.sympify(source)
    return expr.subs({s: constants[s.name] for s in expr.free_symbols if s.name in constants})  # pyright: ignore[reportAttributeAccessIssue, reportReturnType] -- sympy's annotation


def node_count(name: str, desc: data.Array, constants: Mapping[str, Any]) -> int:
    """The nodes of ``desc``'s placement; raises unless every element has its own (node, offset) and every node's
    share fits one HBM node."""
    place = desc.placement
    try:
        place.check(desc.shape, V1.hbm_node_addr_space // desc.dtype.bytes, constants)
    except ValueError as error:
        raise LoweringError(f"{name}: placement {place} does not fit the HBM nodes: {error}") from error
    nodes = int(value(place.nodes, constants))
    if nodes > len(node_bases()):
        raise LoweringError(f"{name}: placement over {nodes} nodes, the model has {len(node_bases())} HBM nodes")
    return nodes


def share_size(desc: data.Array, constants: Mapping[str, Any]) -> int:
    """Elements of one share: the largest node share, padded to 64 bytes (shares are 64-byte aligned)."""
    size = int(numpy.prod([int(value(e, constants)) for e in desc.placement.local_shape(desc.shape)]))
    per_line = 64 // int(desc.dtype.bytes)
    return -(-size // per_line) * per_line


def positions(desc: data.Array, constants: Mapping[str, Any]) -> numpy.ndarray:
    """Per element of ``desc`` in row-major order, its position in the shares laid end to end:
    ``node * share_size + offset``."""
    place = desc.placement
    shape = tuple(int(value(e, constants)) for e in desc.shape)
    params = place.index_map.params
    position = place.node_of(params) * share_size(desc, constants) + place.offset_of(params, shape)
    grid = numpy.indices(shape).reshape(len(shape), -1)
    found = sympy.lambdify(params, value(position, constants), "numpy")(*grid)
    return numpy.broadcast_to(numpy.asarray(found, dtype=numpy.int64), grid.shape[1:])


def shares_code(name: str, desc: data.Array, constants: Mapping[str, Any], ctype: str) -> str:
    """The shares of ``name`` (declared ``extern "C"`` for an argument, defined for a transient) and their table."""
    shares = [share_name(name, node) for node in range(node_count(name, desc, constants))]
    if desc.transient:
        size = share_size(desc, constants)
        lines = [
            f'{ctype} {s}[{size}] __attribute__((section("{section(k)}"), aligned(64)));' for k, s in enumerate(shares)
        ]
    else:
        lines = [f'extern "C" {ctype} {s}[];' for s in shares]
    lines.append(f"static {ctype}* const {table_name(name)}[] = {{{', '.join(shares)}}};")
    return "\n".join(lines)


def blocks(place: placement.Placement) -> list[Any]:
    """Per dimension, the extent of the blocks a node holds contiguously in it, or None if not distributed."""
    if place.pages is not None:
        return list(place.pages.blocks)
    return [None if dim is None else dim.block for dim in place.dims]
