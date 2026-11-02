# Copyright 2026 ETH Zurich and the Alloy authors.
"""The pydantic configuration of every record Alloy reads or writes, and constructors whose errors name the file."""

import pathlib
from collections.abc import Mapping
from typing import Annotated

from pydantic import ConfigDict, Field, TypeAdapter, ValidationError
from pydantic_core import ErrorDetails

#: Strict records: no unknown or missing keys, no type conversion except int to float; NaN and Inf round-trip.
RECORD = ConfigDict(extra="forbid", strict=True, ser_json_inf_nan="constants")
FOREIGN_RECORD = ConfigDict(extra="forbid", strict=True, ser_json_inf_nan="constants", arbitrary_types_allowed=True)

#: A tuple of strings that validates from a JSON array or a list; each item must be a string.
Strings = Annotated[tuple[str, ...], Field(strict=False)]

type Value = bool | int | float | str | list[Value]
#: One size preset of a manifest; ``Mapping`` so a ``dict[str, int]`` is one.
Parameters = Mapping[str, Value]


def error_line(error: ErrorDetails) -> str:
    where = ".".join(str(part) for part in error["loc"]) or "<top level>"
    value = error.get("input")
    shown = error["type"] != "missing" and not isinstance(value, dict | list | tuple)
    return f"{where}: {error['msg']}" + (f", got {value!r}" if shown else "")


def invalid(name: str, path: pathlib.Path, exc: ValidationError) -> ValueError:
    lines = "\n".join(f"  {error_line(e)}" for e in exc.errors(include_url=False))
    return ValueError(f"{path}: not a valid {name}:\n{lines}")


def constructed[R](record: type[R], source: pathlib.Path, /, **fields: object) -> R:
    try:
        return record(**fields)
    except ValidationError as exc:
        raise invalid(record.__name__, source, exc) from exc


def validated_json[R](record: type[R], path: pathlib.Path) -> R:
    try:
        return TypeAdapter(record).validate_json(path.read_bytes())
    except ValidationError as exc:
        raise invalid(record.__name__, path, exc) from exc


def dumped_json(record: object) -> str:
    return TypeAdapter(type(record)).dump_json(record, indent=2).decode()
