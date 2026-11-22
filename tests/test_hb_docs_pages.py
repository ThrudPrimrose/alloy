# Copyright 2026 ETH Zurich and the Alloy authors.
"""The docs-md pages an agent reads hold text it can use: no Sphinx navigation, anchors or images it cannot see."""

import re

from alloy.hb_plugin.pages import PLUGIN, SKILLS, packets_block


def test_the_tt_metal_docs_page_holds_no_raw_html() -> None:
    page = (SKILLS / "tt-metal-docs" / "SKILL.md").read_text()

    leftovers = re.findall(r"<(?:div|span|img|figure)\b[^>]*>", page)

    assert leftovers == [], leftovers[:5]


def test_the_docs_md_packets_of_plugin_toml_list_exactly_the_pages_on_disk() -> None:
    written = PLUGIN.read_text()

    assert packets_block() in written
