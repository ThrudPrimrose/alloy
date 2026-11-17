# Copyright 2026 ETH Zurich and the Alloy authors.
"""The alloy-isa skill page names what the lookup takes: a target, space, swizzle, or tile type the code adds must
reach the agents' page, and every command the page shows must exist."""

import pathlib
import re

import pytest

from alloy.isa import ask, tile
from alloy.isa.__main__ import main

PAGE = (pathlib.Path(ask.__file__).parent.parent / "hb_plugin" / "skills" / "alloy-isa" / "SKILL.md").read_text()


@pytest.mark.parametrize("name", [*ask.TARGETS, *ask.SPACES, *(s for s in ask.SWIZZLES if s != "none")])
def test_the_page_names_every_target_space_and_swizzle_of_ask(name):
    assert f"`{name}`" in PAGE


@pytest.mark.parametrize("in_type", sorted(tile.GPU_BYTES))
def test_the_page_names_every_gpu_tile_input_type(in_type):
    assert f"`{in_type}`" in PAGE or f"`--in {in_type}`" in PAGE


def test_every_command_the_page_shows_exists(capsys):
    commands = set(re.findall(r'command="([a-z-]+)"', PAGE))

    assert {"ask", "ask-all", "host", "lookup", "kernel", "tile", "reverse"} <= commands
    for command in sorted(commands):
        with pytest.raises(SystemExit) as exited:
            main([command, "--help"])
        assert exited.value.code == 0, command
    capsys.readouterr()
