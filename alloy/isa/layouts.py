# Copyright 2026 ETH Zurich and the Alloy authors.
"""Operand layouts as index maps in relayout's algebra (dace-relayout, ``docs/layout.md``): which storage position
holds each element of a 2-D operand. ``ask`` compares two operands by their index maps, so two spellings of one map
are one layout (``row_major:b128`` and ``row_major:xor:8`` on 128-byte rows), and a caller may give any layout as
relayout operations (``--a-layout '[{"action": "block", ...}]'``).

The named forms are relayout operations over the operand's digits ``i0`` (rows) and ``i1`` (columns):

- ``col_major``: ``permute`` to ``[i1, i0]``;
- a swizzle renumbers the 16-byte chunks of each stored row: the inner digit is ``block`` ed into the chunk ``c``
  and the element within it, then ``shuffle`` d. ``b128``, ``b64`` and ``b32`` are the sm90 tensor-map swizzles
  (CUTLASS ``Swizzle<B, 4, 3>``, B = 3, 2, 1: address bits 4.. XOR bits 7..), chunk ``c`` of row ``r`` of ``RC``
  chunks stored at ``c ^ (((r * RC + c) >> 3) % 2^B)``; ``xor:8`` is the CDNA LDS swizzle ``c ^ (r % 8)``.
"""

import functools
import json
from collections.abc import Sequence

import numpy
from relayout import requests  # type: ignore[import-untyped]
from relayout.expr import evaluate  # type: ignore[import-untyped]
from relayout.ops import ArraySpec, run  # type: ignore[import-untyped]

#: Bytes of an element, per type an operand may name.
BYTES = {"f64": 8, "f32": 4, "tf32": 4, "f16": 2, "bf16": 2, "e4m3": 1, "e5m2": 1, "i64": 8, "i32": 4, "i8": 1}
#: Per sm90 swizzle: B, the chunk bits it XORs.
SPAN_BITS = {"b32": 1, "b64": 2, "b128": 3}
CHUNK = 16


def named(shape: tuple[int, int], dtype: str, layout: str, swizzle: str) -> list[dict[str, object]]:
    """The relayout operations of a named layout and swizzle on a ``shape`` operand of ``dtype``; ValueError when the
    swizzle does not fit the stored rows (whole 16-byte chunks, a multiple of the chunks it XORs)."""
    operations: list[dict[str, object]] = []
    outer, inner = ("i0", "i1") if layout == "row_major" else ("i1", "i0")
    if layout == "col_major":
        operations.append({"action": "permute", "array": "x", "order": ["i1", "i0"]})
    if swizzle == "none":
        return operations
    width = shape[1] if layout == "row_major" else shape[0]
    size = BYTES[dtype]
    bits = SPAN_BITS.get(swizzle, 3)
    chunks, rest = divmod(width * size, CHUNK)
    if rest or chunks % (1 << bits):
        raise ValueError(
            f"swizzle {swizzle} renumbers 16-byte chunks in groups of {1 << bits}; a stored row of {width} {dtype} is "
            f"{width * size} bytes"
        )
    if swizzle == "xor:8":
        stored = f"c ^ ({outer} % 8)"
    else:
        stored = f"c ^ ((({outer} * {chunks} + c) >> 3) % {1 << bits})"
    return [
        *operations,
        {"action": "block", "array": "x", "digit": inner, "factor": CHUNK // size, "into": ["c", "e"]},
        {"action": "shuffle", "array": "x", "digits": [outer, "c"], "f": [outer, stored], "f_inv": [outer, stored]},
    ]


@functools.lru_cache(maxsize=256)
def offsets(shape: tuple[int, int], operations: str) -> tuple[int, ...]:
    """The storage position of each element, row-major over ``shape``, under the relayout ``operations`` (JSON);
    ValueError when they are not a layout of the operand (a pad, a distribution, or not a bijection)."""
    found = requests.parse_requests({"startup": {"load": [], "grid": ["P"]}, "operations": json.loads(operations)})
    state = run(found.operations, [ArraySpec("x", 2)], [1], "layout")
    index_map = state.arrays["x"].digits.index_map([str(n) for n in shape], "layout")
    rows, cols = numpy.meshgrid(numpy.arange(shape[0]), numpy.arange(shape[1]), indexing="ij")
    names = {"r": rows.ravel(), "c": cols.ravel()}
    calls = {"min": min, "max": max}
    position = [
        numpy.broadcast_to(evaluate(e, names, calls, "layout"), rows.size) for e in index_map.physical(["r", "c"])
    ]
    extents = [int(evaluate(e, {}, calls, "layout")) for e in index_map.extents()]
    flat = numpy.zeros(rows.size, dtype=numpy.int64)
    for value, extent in zip(position, extents, strict=True):
        flat = flat * extent + value
    if sorted(flat.tolist()) != list(range(rows.size)):
        raise ValueError(f"the operations {operations} do not lay out a {shape[0]}x{shape[1]} operand one to one")
    return tuple(flat.tolist())


def index_map(shape: Sequence[int], dtype: str, layout: str, swizzle: str, given: str = "") -> tuple[int, ...] | None:
    """The operand's index map: from its relayout operations ``given`` (JSON), else from its named layout and swizzle;
    None for an operand that is not 2-D, or a swizzle that does not fit it."""
    if len(shape) != 2:
        return None
    rows, cols = int(shape[0]), int(shape[1])
    try:
        text = given or json.dumps(named((rows, cols), dtype, layout, swizzle))
        return offsets((rows, cols), text)
    except (ValueError, KeyError):
        return None


def problem(shape: Sequence[int], given: str) -> str:
    """Why the relayout operations ``given`` (JSON) are not a layout of a ``shape`` operand; ``""`` when they are."""
    if len(shape) != 2:
        return f"a layout as relayout operations needs a 2-D operand, not shape {list(shape)}"
    try:
        operations = json.loads(given)
        if not isinstance(operations, list):
            return "the layout is a JSON list of relayout operations on array x"
        offsets((int(shape[0]), int(shape[1])), json.dumps(operations))
    except (ValueError, KeyError, TypeError) as exc:
        return str(exc).splitlines()[0][:300]
    return ""
