# Copyright 2026 ETH Zurich and the Alloy authors.
"""The type of a parsed TOML or JSON table, shared by the modules that read row files, verdicts and task lists."""

from typing import Any

#: A TOML or JSON table: string keys, values as the file holds them.
Json = dict[str, Any]
