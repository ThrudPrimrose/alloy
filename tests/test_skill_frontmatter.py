# Copyright 2026 ETH Zurich and the Alloy authors.
"""Every skill page's frontmatter is YAML the bench can load (an unquoted ``refused: ...`` broke packet staging)."""

import pathlib

import pytest
import yaml

SKILLS = sorted((pathlib.Path(__file__).parent.parent / "alloy" / "hb_plugin" / "skills").glob("*/SKILL.md"))


@pytest.mark.parametrize("page", SKILLS, ids=lambda p: p.parent.name)
def test_a_skill_page_frontmatter_is_yaml_with_a_name_and_description(page: pathlib.Path) -> None:
    head = yaml.safe_load(page.read_text().split("---", 2)[1])

    assert head["name"] == page.parent.name and head["description"]
