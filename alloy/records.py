# Copyright 2026 ETH Zurich and the Alloy authors.
"""The pydantic configuration of every record Alloy reads from or writes to a file, and the constructors that name
the file in the error of a record that fails validation."""

import pathlib
from collections.abc import Mapping
from typing import Annotated

from pydantic import ConfigDict, Field, TypeAdapter, ValidationError
from pydantic_core import ErrorDetails

#: Validation refuses unknown keys, missing required keys and any conversion between types (``"1"`` is no int,
#: ``1`` is no bool); the one conversion accepted is an int as a float. JSON writes NaN and the infinities as
#: ``NaN`` and ``Infinity``, which the JSON validator reads back.
RECORD = ConfigDict(extra="forbid", strict=True, ser_json_inf_nan="constants")
#: :data:`RECORD` for a record holding a type pydantic has no schema for, checked by ``isinstance``.
FOREIGN_RECORD = ConfigDict(extra="forbid", strict=True, ser_json_inf_nan="constants", arbitrary_types_allowed=True)

#: A tuple of strings that validates from a JSON array or a list; each item must be a string.
Strings = Annotated[tuple[str, ...], Field(strict=False)]

#: A manifest parameter value: a size, a scalar argument, a flag, or a list of them.
type Value = bool | int | float | str | list[Value]
#: One size preset of a manifest by parameter name. ``Mapping`` so a ``dict[str, int]`` is one.
Parameters = Mapping[str, Value]


def error_line(error: ErrorDetails) -> str:
    """``<dotted location>: <message>``, followed by the offending value unless it is a table or an array."""
    where = ".".join(str(part) for part in error["loc"]) or "<top level>"
    value = error.get("input")
    shown = error["type"] != "missing" and not isinstance(value, dict | list | tuple)
    return f"{where}: {error['msg']}" + (f", got {value!r}" if shown else "")


def invalid(name: str, path: pathlib.Path, exc: ValidationError) -> ValueError:
    """The error naming ``path``, the record ``name`` and every failing key of ``exc``."""
    lines = "\n".join(f"  {error_line(e)}" for e in exc.errors(include_url=False))
    return ValueError(f"{path}: not a valid {name}:\n{lines}")


def constructed[R](record: type[R], source: pathlib.Path, /, **fields: object) -> R:
    """``record(**fields)``, whose values were read from ``source``."""
    try:
        return record(**fields)
    except ValidationError as exc:
        raise invalid(record.__name__, source, exc) from exc


def validated_json[R](record: type[R], path: pathlib.Path) -> R:
    """The JSON file ``path`` as a ``record``."""
    try:
        return TypeAdapter(record).validate_json(path.read_bytes())
    except ValidationError as exc:
        raise invalid(record.__name__, path, exc) from exc


def dumped_json(record: object) -> str:
    """``record`` as indented JSON, the form :func:`validated_json` reads."""
    return TypeAdapter(type(record)).dump_json(record, indent=2).decode()
