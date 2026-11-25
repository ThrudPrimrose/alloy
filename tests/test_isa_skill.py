# Copyright 2026 ETH Zurich and the Alloy authors.
"""The alloy-isa skill page names what the lookup takes: a target, space, swizzle, or tile type the code adds must
reach the agents' page, and every command the page shows must exist."""

import pathlib
import re

import pytest

from alloy.isa import ask, tile
from alloy.isa.__main__ import main

PAGE = (pathlib.Path(ask.__file__).parent.parent / "hb_plugin" / "skills" / "alloy-isa" / "SKILL.md").read_text()


def test_the_page_names_every_target_space_and_swizzle_of_ask() -> None:
    names = [*ask.TARGETS, *ask.SPACES, *(s for s in ask.SWIZZLES if s != "none")]

    assert [name for name in names if f"`{name}`" not in PAGE] == []


def test_the_page_names_every_gpu_tile_input_type() -> None:
    assert [t for t in sorted(tile.GPU_BYTES) if f"`{t}`" not in PAGE and f"`--in {t}`" not in PAGE] == []


def test_every_command_the_page_shows_exists(capsys: pytest.CaptureFixture[str]) -> None:
    commands = set(re.findall(r'command="([a-z-]+)"', PAGE))

    assert {"ask", "ask-all", "host", "lookup", "kernel", "tile", "reverse"} <= commands
    for command in sorted(commands):
        with pytest.raises(SystemExit) as exited:
            main([command, "--help"])
        assert exited.value.code == 0, command
    capsys.readouterr()


def test_the_cpu_mma_and_the_broadcast_source_the_page_shows_are_feasible() -> None:
    mma = re.search(r"`--a (\S+) --b (\S+) --c (\S+)`", PAGE)
    scalar = re.search(r"scalar source as\s+`--x (\S+)`", PAGE)
    assert mma is not None and scalar is not None
    a, b, c = (ask.Operand.parse(text) for text in mma.groups())

    product = ask.ask(ask.Request("avx512", "mma", {"a": a, "b": b, "c": c}), verify=False)
    broadcast = ask.ask(ask.Request("avx512", "broadcast", {"x": ask.Operand.parse(scalar.group(1))}), verify=False)

    assert isinstance(product, ask.Feasible) and isinstance(broadcast, ask.Feasible)
