# Copyright 2026 ETH Zurich and the Alloy authors.
"""Every skill page's frontmatter is YAML the bench can load (an unquoted ``refused: ...`` broke packet staging)."""

import pathlib

import yaml

SKILLS = sorted((pathlib.Path(__file__).parent.parent / "alloy" / "hb_plugin" / "skills").glob("*/SKILL.md"))


def test_every_skill_page_frontmatter_is_yaml_with_its_name_and_a_description() -> None:
    heads = {page.parent.name: yaml.safe_load(page.read_text().split("---", 2)[1]) for page in SKILLS}

    assert SKILLS and {name: (h["name"], bool(h["description"])) for name, h in heads.items()} == {
        name: (name, True) for name in heads
    }
