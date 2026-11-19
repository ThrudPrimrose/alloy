# Copyright 2026 ETH Zurich and the Alloy authors.
"""The facts page of a target holds every fact the lookup prints for it, and the plugin's static page is the page as
the generator renders it now (content parity of the facts-page and tool configurations)."""

import re

import pytest

from alloy.hb_plugin import pages as skill_pages
from alloy.isa import pages, softhier, tensix
from alloy.isa.__main__ import main

#: The title of an answer: ``<target>/<dtype>/<op>: `` (the page names the dtypes it covers there).
TITLE = re.compile(r"^(tensix|softhier)/[^/]+/[^:]+: ")


def sections(page: str) -> dict[str, str]:
    """The page's text per op section (``## <op>``)."""
    parts = re.split(r"^## (\S+)$", page, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def missing(answer: str, section: str) -> list[str]:
    """The lines of a lookup answer that its op's section of the page lacks."""
    said = (TITLE.sub("", line).strip() for line in answer.splitlines())
    return [line for line in said if line and line not in section]


def lookup(capsys: pytest.CaptureFixture[str], *argv: str) -> str:
    main(["lookup", *argv])
    return capsys.readouterr().out


def test_the_tensix_page_holds_every_line_the_lookup_prints_for_every_row_rung_and_dtype(
    capsys: pytest.CaptureFixture[str],
):
    page = pages.tensix_page()
    by_op = sections(page)
    target_note = pages.tensix_target_note().strip()

    for op in {r.op for r in tensix.rows()}:
        for dtype in tensix.dtypes():
            answer = lookup(capsys, "tensix", op, dtype)
            assert missing(answer.replace(target_note, ""), by_op[op]) == [], (op, dtype)
    assert target_note in page


def test_the_softhier_page_holds_every_line_the_lookup_prints_for_every_row_and_dtype(
    capsys: pytest.CaptureFixture[str],
):
    page = pages.softhier_page()
    by_op = sections(page)
    tail = pages.softhier_tail()

    for op in {r.op for r in softhier.rows()}:
        typed = {d for r in softhier.rows() if r.op == op and not softhier.untyped(r) for d in r.dtypes}
        for dtype in typed or {"f32"}:
            answer = lookup(capsys, "softhier", op, dtype)
            assert missing("\n".join(line for line in answer.splitlines() if line not in tail), by_op[op]) == []
    assert all(line in page for line in tail)


@pytest.mark.parametrize("target", sorted(skill_pages.FACTS))
def test_the_plugins_facts_page_is_the_generators_page_now(target: str):
    path = skill_pages.SKILLS / f"alloy-facts-{target}" / "SKILL.md"

    assert path.read_text() == skill_pages.facts_page(target), "rerun: python -m alloy.hb_plugin.pages facts"


@pytest.mark.parametrize(
    ("text", "left_out"),
    [
        ("relu_tile\n=========\n\n.. doxygenfunction:: relu_tile_init()\n.. doxygenfunction:: relu_tile(uint32_t)\n", True),
        ("Compute APIs\n============\n\nThis page lists the APIs.\n\n.. doxygenfunction:: add_tiles\n", False),
        ("Tiles\n=====\n\nA tile is 32x32.\n", False),
    ],
)  # fmt: skip
def test_a_docs_page_is_left_out_only_when_the_headers_hold_all_its_text(text: str, left_out: bool):
    assert skill_pages.doxygen_only(text) is left_out


@pytest.mark.parametrize("target", sorted(pages.ASKED))
def test_the_page_holds_every_line_ask_prints_for_its_waits_barriers_and_gemm_plan(
    target: str, capsys: pytest.CaptureFixture[str]
):
    asked = sections(pages.page(target))["Asked"]
    for text in pages.ASKED[target]:
        op, *fields = text.split()
        flags = [word for field in fields for word in (f"--{field.split('=')[0]}", field.split("=", 1)[1])]
        main(["ask", target, op, *flags, "--no-verify"])
        first, *rest = capsys.readouterr().out.splitlines()
        assert f"ask {target} {text}: {first.split(': ', 1)[1]}" in asked, text
        assert [line for line in rest if line and line not in asked] == [], text
