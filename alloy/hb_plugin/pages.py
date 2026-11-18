# Copyright 2026 ETH Zurich and the Alloy authors.
"""The static skill pages of the agent-study configurations (notes: design-review-2026-11-18, "Ablation").

    python -m alloy.hb_plugin.pages facts            # skills/alloy-facts-<target>/SKILL.md from `alloy.isa page`
    python -m alloy.hb_plugin.pages docs TREE         # skills/tt-metal-*/SKILL.md from a tt-metal v0.63.0 tree

facts-page: the text of ``python -m alloy.isa page <target>``, the lookup's own lines (alloy/isa/pages.py).

docs-md: the pages :data:`RULE` selects (docs_manifest.json records the tree, pandoc and every source).
"""

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys

from alloy.isa import pages

__all__ = ["COMPUTE_API", "DATAFLOW_API", "DOCS", "MANIFEST", "RULE", "SKILLS", "docs_pages", "facts_page", "main"]

SKILLS = pathlib.Path(__file__).parent / "skills"
MANIFEST = pathlib.Path(__file__).parent / "docs_manifest.json"

#: What docs-md holds: one rule, fixed before any eval run (fairness F17), not what a pilot needed.
RULE = """\
  * tt-metal-compute-api: tt_metal/include/compute_kernel_api.h and every file under tt_metal/include/compute_kernel_api/,
    verbatim, doc comments included;
  * tt-metal-dataflow-api: tt_metal/hw/inc/dataflow_api.h, verbatim;
  * tt-metal-docs: METALIUM_GUIDE.md, then every page of docs/source/tt-metalium/tt_metal/ under programming_model/,
    advanced_topics/, examples/ and apis/kernel_apis/, in path order, converted from reStructuredText by pandoc
    (gfm); a page that is only doxygen directives is left out, since its text is the header's doc comment above.
The tree is tt-metal v0.63.0 with tt-llk at the commit it pins (identical to the ttnn 0.63.0 wheel's sources the card
compiles against).
"""

#: The compute API: the umbrella header and its folder.
COMPUTE_API = ("tt_metal/include/compute_kernel_api.h", "tt_metal/include/compute_kernel_api")
#: The data-movement (reader and writer) API.
DATAFLOW_API = ("tt_metal/hw/inc/dataflow_api.h",)
#: The kernel-writing pages of the tt-metalium docs.
DOCS_ROOT = "docs/source/tt-metalium/tt_metal"
DOCS = ("programming_model", "advanced_topics", "examples", "apis/kernel_apis")
GUIDE = "METALIUM_GUIDE.md"

FACTS = {
    "tensix": (
        "Alloy's checked facts for Tenstorrent Tensix (Blackhole): every compute-kernel tile call with its includes, "
        "init and call per tt-metal version, the platform each verdict ran on and its measured error, and the SFPU "
        "math kernels (SFPI) measured on a Blackhole card, with their code.",
        "before writing a Tensix compute, reader or writer kernel, and before calling a tile operation or a math "
        "function on Tensix.",
    ),
    "softhier": (
        "Alloy's checked facts for SoftHier v1: the C code of every vector (Spatz RVV), copy (iDMA), matrix (RedMulE) "
        "and barrier row with its GVSoC verdict, and the build line.",
        "before writing a SoftHier kernel.",
    ),
}
DOCS_PAGES = {
    "tt-metal-compute-api": (
        "The tt-metal v0.63.0 compute kernel API headers (compute_kernel_api.h and compute_kernel_api/), verbatim with "
        "their doc comments.",
        "before writing a Tensix compute kernel or calling a compute API function.",
    ),
    "tt-metal-dataflow-api": (
        "The tt-metal v0.63.0 data-movement API header (dataflow_api.h), verbatim with its doc comments.",
        "before writing a Tensix reader or writer kernel.",
    ),
    "tt-metal-docs": (
        "The tt-metal v0.63.0 documentation on writing kernels: METALIUM_GUIDE.md and the tt-metalium pages on the "
        "programming model, tiles, memory, compute engines, the examples and the kernel APIs.",
        "before writing any Tensix kernel, to learn the programming model and the kernel APIs.",
    ),
}


def skill(name: str, description: str, when: str, body: str) -> str:
    """A skill page; trailing blanks are cut from every line, as the repository's pre-commit hooks would."""
    head = ["---", f"name: {name}", f"description: {json.dumps(description)}", f"when: {when}", "---", ""]
    lines = [*head, *body.rstrip("\n").splitlines()]
    return "\n".join(line.rstrip() for line in lines) + "\n"


def facts_page(target: str) -> str:
    description, when = FACTS[target]
    return skill(f"alloy-facts-{target}", description, when, pages.page(target))


def files(tree: pathlib.Path, roots: tuple[str, ...], suffix: str = "") -> list[pathlib.Path]:
    """Every file under ``roots`` (a file or a folder), in path order."""
    found: list[pathlib.Path] = []
    for root in roots:
        path = tree / root
        found += [path] if path.is_file() else sorted(p for p in path.rglob(f"*{suffix}") if p.is_file())
    return found


def headers_body(tree: pathlib.Path, title: str, sources: list[pathlib.Path]) -> str:
    out = [f"# {title}", ""]
    for path in sources:
        out += [f"## {path.relative_to(tree)}", "", "```cpp", path.read_text().rstrip("\n"), "```", ""]
    return "\n".join(out)


def underline(line: str) -> bool:
    return bool(line) and not set(line) - set("=-*~^#")


def doxygen_only(text: str) -> bool:
    """A docs page whose content is pulled from the headers: no line but titles, their underlines and directives."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    prose = [
        line
        for line, after in zip(lines, [*lines[1:], ""], strict=True)
        if not line.startswith("..") and not underline(line) and not underline(after)
    ]
    return not prose and any(line.startswith(".. doxygen") for line in lines)


def converted(path: pathlib.Path) -> str:
    done = subprocess.run(["pandoc", "--from", "rst", "--to", "gfm", "--wrap", "none", str(path)],
                          capture_output=True, text=True, check=True, timeout=120)  # fmt: skip
    return done.stdout


def doc_sources(tree: pathlib.Path) -> list[pathlib.Path]:
    pages_ = files(tree, tuple(f"{DOCS_ROOT}/{d}" for d in DOCS), ".rst")
    return [tree / GUIDE, *(p for p in pages_ if not doxygen_only(p.read_text()))]


def docs_body(tree: pathlib.Path, sources: list[pathlib.Path]) -> str:
    out = ["# tt-metal v0.63.0 documentation on writing kernels", ""]
    for path in sources:
        text = path.read_text() if path.suffix == ".md" else converted(path)
        out += [f"## Source: {path.relative_to(tree)}", "", text.rstrip("\n"), ""]
    return "\n".join(out)


def tree_commit(tree: pathlib.Path) -> str:
    done = subprocess.run(["git", "-C", str(tree), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
    return done.stdout.strip()


def docs_pages(tree: pathlib.Path) -> tuple[dict[str, str], dict]:
    """The three docs-md pages and their manifest."""
    sources = {
        "tt-metal-compute-api": files(tree, COMPUTE_API),
        "tt-metal-dataflow-api": files(tree, DATAFLOW_API),
        "tt-metal-docs": doc_sources(tree),
    }
    bodies = {
        "tt-metal-compute-api": headers_body(tree, "tt-metal v0.63.0 compute kernel API", sources["tt-metal-compute-api"]),
        "tt-metal-dataflow-api": headers_body(tree, "tt-metal v0.63.0 data-movement API", sources["tt-metal-dataflow-api"]),
        "tt-metal-docs": docs_body(tree, sources["tt-metal-docs"]),
    }  # fmt: skip
    built = {name: skill(name, *DOCS_PAGES[name], bodies[name]) for name in DOCS_PAGES}
    version = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    manifest = {
        "rule": RULE,
        "tree_commit": tree_commit(tree),
        "pandoc": version,
        "pages": {
            name: {
                "bytes": len(built[name].encode()),
                "sources": {
                    str(p.relative_to(tree)): hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in sources[name]
                },
            }
            for name in DOCS_PAGES
        },
    }
    return built, manifest


def write(name: str, text: str) -> pathlib.Path:
    path = SKILLS / name / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m alloy.hb_plugin.pages", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("facts", help="the facts pages of every target")
    docs_p = commands.add_parser("docs", help="the docs-md pages from a tt-metal tree")
    docs_p.add_argument("tree", type=pathlib.Path)
    args = parser.parse_args(argv)
    if args.command == "facts":
        for target in FACTS:
            path = write(f"alloy-facts-{target}", facts_page(target))
            print(f"{path}: {path.stat().st_size} bytes")
        return 0
    built, manifest = docs_pages(args.tree)
    for name, text in built.items():
        path = write(name, text)
        print(f"{path}: {len(text.encode())} bytes")
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
