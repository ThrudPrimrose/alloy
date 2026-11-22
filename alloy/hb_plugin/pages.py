# Copyright 2026 ETH Zurich and the Alloy authors.
"""The docs-md pages of the agent-study ablation (none, docs-md, tool): each tool target's vendor documentation as
markdown skill pages, one packet per target.

    python -m alloy.hb_plugin.pages tensix TREE          # the tt-metal pages from a tt-metal v0.63.0 tree
    python -m alloy.hb_plugin.pages softhier TREE        # the RVV 1.0 spec and the softhier-sdk headers from its tree
    python -m alloy.hb_plugin.pages x86|arm|sm90|gfx942|gfx90a

A PDF is downloaded, its SHA-256 recorded, and converted by pymupdf4llm; run the PDF packets under
``uv run --with pymupdf4llm==2.1``. docs_manifest.json records, per packet, the rule, every source and every page; the
``docs-md-<packet>`` packets of plugin.toml are rewritten from the pages on disk.
"""

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass

from alloy.jsontype import Json

__all__ = [
    "COMPUTE_API",
    "DATAFLOW_API",
    "DOCS",
    "ISA",
    "MANIFEST",
    "PLUGIN",
    "RULE",
    "SKILLS",
    "docs_pages",
    "main",
    "packets_block",
]

SKILLS = pathlib.Path(__file__).parent / "skills"
MANIFEST = pathlib.Path(__file__).parent / "docs_manifest.json"
PLUGIN = pathlib.Path(__file__).parent / "plugin.toml"
CACHE = pathlib.Path.home() / ".cache" / "alloy-docs"

#: What docs-md holds: one rule, fixed before any eval run (fairness F17), not what a pilot needed.
RULE = """\
docs-md is the vendor's own reference for the task's target, converted to markdown and nothing added:
  * tensix: tt-metal v0.63.0 (tt-llk at the commit it pins): tt_metal/include/compute_kernel_api.h and every file under
    tt_metal/include/compute_kernel_api/, verbatim; tt_metal/hw/inc/dataflow_api.h, verbatim; METALIUM_GUIDE.md, then
    every page of docs/source/tt-metalium/tt_metal/ under programming_model/, advanced_topics/, examples/ and
    apis/kernel_apis/, in path order, converted from reStructuredText by pandoc (gfm), leaving out a page that is only
    doxygen directives;
  * x86 (avx2, avx512, avx512_fp16): the Intel 64 and IA-32 Architectures Software Developer's Manual, Volume 2;
  * arm (neon, sve, sme): the Arm C Language Extensions (acle.md and neon_intrinsics/advsimd.md) at a pinned commit;
  * sm90: the PTX ISA of the CUDA version the bench image ships (13.4: PTX ISA 9.4);
  * gfx942: the AMD Instinct MI300 CDNA3 ISA reference; gfx90a: the AMD Instinct MI200 CDNA2 ISA reference;
  * softhier: the RISC-V V extension 1.0 spec (Spatz runs RVV) and softhier-sdk's README.md and
    runtime/runtime/include/*.h, verbatim, at the commit isa/softhier_pins.toml pins.
A PDF becomes one page per entry of its outline at the shallowest level with more than one entry (one page when it
has no outline), converted by pymupdf4llm; a markdown source one page per heading at that level.
"""

#: The compute API: the umbrella header and its folder.
COMPUTE_API = ("tt_metal/include/compute_kernel_api.h", "tt_metal/include/compute_kernel_api")
#: The data-movement (reader and writer) API.
DATAFLOW_API = ("tt_metal/hw/inc/dataflow_api.h",)
#: The kernel-writing pages of the tt-metalium docs.
DOCS_ROOT = "docs/source/tt-metalium/tt_metal"
DOCS = ("programming_model", "advanced_topics", "examples", "apis/kernel_apis")
GUIDE = "METALIUM_GUIDE.md"

TT_PAGES = {
    "tt-metal-compute-api": (
        (
            "The tt-metal v0.63.0 compute kernel API headers (compute_kernel_api.h and compute_kernel_api/), verbatim with "
            "their doc comments."
        ),
        "before writing a Tensix compute kernel or calling a compute API function.",
    ),
    "tt-metal-dataflow-api": (
        "The tt-metal v0.63.0 data-movement API header (dataflow_api.h), verbatim with its doc comments.",
        "before writing a Tensix reader or writer kernel.",
    ),
    "tt-metal-docs": (
        (
            "The tt-metal v0.63.0 documentation on writing kernels: METALIUM_GUIDE.md and the tt-metalium pages on the "
            "programming model, tiles, memory, compute engines, the examples and the kernel APIs."
        ),
        "before writing any Tensix kernel, to learn the programming model and the kernel APIs.",
    ),
}

ACLE = "https://raw.githubusercontent.com/ARM-software/acle/74fa229b09d1c5af533a88e387e470c26494953f"


@dataclass(frozen=True)
class Source:
    """A downloaded document: its short title (each page names it) and where it is fetched from."""

    title: str
    url: str


#: The downloaded sources of each packet, and the targets it is for.
ISA: dict[str, tuple[str, tuple[Source, ...]]] = {
    "x86": ("x86 AVX2, AVX-512 and AVX-512 FP16", (
        Source("Intel SDM Vol. 2", "https://cdrdv2-public.intel.com/671110/325383-sdm-vol-2abcd.pdf"),
    )),
    "arm": ("Arm NEON, SVE and SME", (
        Source("Arm ACLE", f"{ACLE}/main/acle.md"),
        Source("Arm ACLE Advanced SIMD intrinsics", f"{ACLE}/neon_intrinsics/advsimd.md"),
    )),
    "sm90": ("NVIDIA sm90 (PTX)", (Source("PTX ISA 9.4", "https://docs.nvidia.com/cuda/pdf/ptx_isa_9.4.pdf"),)),
    "gfx942": ("AMD gfx942 (CDNA3)", (Source("AMD CDNA3 ISA", (
        "https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/instruction-set-architectures/"
        "amd-instinct-mi300-cdna3-instruction-set-architecture.pdf"
    )),)),
    "gfx90a": ("AMD gfx90a (CDNA2)", (Source("AMD CDNA2 ISA", (
        "https://www.amd.com/content/dam/amd/en/documents/instinct-tech-docs/instruction-set-architectures/"
        "instinct-mi200-cdna2-instruction-set-architecture.pdf"
    )),)),
    "softhier": ("SoftHier v1", (
        Source("RISC-V V 1.0", "https://github.com/riscv/riscv-v-spec/releases/download/v1.0/riscv-v-spec-1.0.pdf"),
    )),
}  # fmt: skip
#: The softhier-sdk files a softhier page holds verbatim, relative to its tree.
SOFTHIER_SDK = ("README.md", "runtime/runtime/include")


def skill(name: str, description: str, when: str, body: str) -> str:
    """A skill page; trailing blanks are cut from every line, as the repository's pre-commit hooks would."""
    head = ["---", f"name: {name}", f"description: {json.dumps(description)}", f"when: {json.dumps(when)}", "---", ""]
    lines = [*head, *body.rstrip("\n").splitlines()]
    return "\n".join(line.rstrip() for line in lines) + "\n"


def files(tree: pathlib.Path, roots: tuple[str, ...], suffix: str = "") -> list[pathlib.Path]:
    """Every file under ``roots`` (a file or a folder), in path order."""
    found: list[pathlib.Path] = []
    for root in roots:
        path = tree / root
        found += [path] if path.is_file() else sorted(p for p in path.rglob(f"*{suffix}") if p.is_file())
    return found


def verbatim_body(tree: pathlib.Path, title: str, sources: list[pathlib.Path]) -> str:
    out = [f"# {title}", ""]
    for path in sources:
        fence = "markdown" if path.suffix == ".md" else "cpp"
        out += [f"## {path.relative_to(tree)}", "", f"```{fence}", path.read_text().rstrip("\n"), "```", ""]
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


def digests(tree: pathlib.Path, sources: list[pathlib.Path]) -> dict[str, str]:
    return {str(p.relative_to(tree)): hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in sources}


def docs_pages(tree: pathlib.Path) -> tuple[dict[str, str], Json]:
    """The three tensix pages and their manifest."""
    sources = {
        "tt-metal-compute-api": files(tree, COMPUTE_API),
        "tt-metal-dataflow-api": files(tree, DATAFLOW_API),
        "tt-metal-docs": doc_sources(tree),
    }
    bodies = {
        "tt-metal-compute-api": verbatim_body(tree, "tt-metal v0.63.0 compute kernel API", sources["tt-metal-compute-api"]),
        "tt-metal-dataflow-api": verbatim_body(tree, "tt-metal v0.63.0 data-movement API", sources["tt-metal-dataflow-api"]),
        "tt-metal-docs": docs_body(tree, sources["tt-metal-docs"]),
    }  # fmt: skip
    built = {name: skill(name, *TT_PAGES[name], bodies[name]) for name in TT_PAGES}
    version = subprocess.run(["pandoc", "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    manifest = {
        "tree_commit": tree_commit(tree),
        "pandoc": version,
        "pages": {
            name: {"bytes": len(built[name].encode()), "sources": digests(tree, sources[name])} for name in built
        },
    }
    return built, manifest


def fetched(source: Source) -> pathlib.Path:
    """``source`` in the download cache, fetched once."""
    path = CACHE / hashlib.sha256(source.url.encode()).hexdigest()[:16] / source.url.rsplit("/", 1)[-1]
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        request = urllib.request.Request(source.url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
        with urllib.request.urlopen(request, timeout=600) as response:
            path.write_bytes(response.read())
    return path


def chapter_level(levels: list[int]) -> int | None:
    """The shallowest outline level with more than one entry, or None for a flat document."""
    return next((lv for lv in sorted(set(levels)) if levels.count(lv) > 1), None)


def pdf_chapters(path: pathlib.Path) -> list[tuple[str, str]]:
    """``(title, markdown)`` per outline entry at :func:`chapter_level`; the whole PDF when it has no outline."""
    import pymupdf  # type: ignore[import-not-found,unused-ignore]
    import pymupdf4llm  # type: ignore[import-not-found,unused-ignore]

    doc = pymupdf.open(path)
    toc = doc.get_toc(simple=True)
    level = chapter_level([entry[0] for entry in toc])
    if level is None:
        return [("", pymupdf4llm.to_markdown(doc, show_progress=False))]
    starts = [(title, page - 1) for lv, title, page in toc if lv == level and page > 0]
    ends = [start for _, start in starts[1:]] + [doc.page_count]
    return [
        (
            title.strip(),
            pymupdf4llm.to_markdown(doc, pages=list(range(start, max(end, start + 1))), show_progress=False),
        )
        for (title, start), end in zip(starts, ends, strict=True)
    ]


def md_chapters(text: str) -> list[tuple[str, str]]:
    """``(title, markdown)`` per heading at :func:`chapter_level`, outside code fences."""
    lines, fenced, heads = text.splitlines(), False, []
    for i, line in enumerate(lines):
        fenced ^= line.startswith("```")
        if not fenced and (m := re.match(r"^(#+) (.+)$", line)):
            heads.append((len(m.group(1)), m.group(2).strip(), i))
    level = chapter_level([lv for lv, _, _ in heads])
    if level is None:
        return [("", text)]
    cuts = [(title, i) for lv, title, i in heads if lv == level]
    ends = [i for _, i in cuts[1:]] + [len(lines)]
    return [(title, "\n".join(lines[i:end])) for (title, i), end in zip(cuts, ends, strict=True)]


def slug(title: str) -> str:
    return "-".join(re.findall(r"[a-z0-9]+", title.lower()))[:40].strip("-") or "all"


def isa_pages(packet: str, tree: pathlib.Path | None) -> tuple[dict[str, str], Json]:
    """The pages of ``packet`` (:data:`ISA`) and their manifest."""
    targets, sources = ISA[packet]
    built: dict[str, str] = {}
    recorded: dict[str, str] = {}
    for source in sources:
        path = fetched(source)
        recorded[source.url] = hashlib.sha256(path.read_bytes()).hexdigest()
        chapters = pdf_chapters(path) if path.suffix == ".pdf" else md_chapters(path.read_text())
        for title, body in chapters:
            name = f"docs-md-{packet}-{len(built) + 1:02d}-{slug(title)}"
            part = f"{source.title}: {title}" if title else source.title
            built[name] = skill(name, f"{part} (vendor documentation for {targets}).",
                                f"when you need {part} while writing a kernel for {targets}.", body)  # fmt: skip
    manifest: dict[str, Json] = {"sources": recorded}
    if packet == "softhier":
        if tree is None:
            raise SystemExit("softhier: pass the softhier-sdk tree")
        sdk = files(tree, SOFTHIER_SDK)
        name = f"docs-md-softhier-{len(built) + 1:02d}-softhier-sdk"
        built[name] = skill(name, "softhier-sdk's README.md and runtime headers, verbatim (vendor documentation for "
                            "SoftHier v1).", "before writing a SoftHier kernel or calling a flex_* runtime function.",
                            verbatim_body(tree, "softhier-sdk", sdk))  # fmt: skip
        manifest["tree_commit"] = tree_commit(tree)
        manifest["tree_sources"] = digests(tree, sdk)
    manifest["pages"] = {name: len(text.encode()) for name, text in built.items()}
    return built, manifest


#: The generated block of plugin.toml.
BEGIN = "# BEGIN docs-md packets: written by `python -m alloy.hb_plugin.pages`, from the pages on disk\n"
END = "# END docs-md packets\n"


def packets_block() -> str:
    pages = sorted(p.parent.name for p in SKILLS.glob("docs-md-*/SKILL.md"))
    out = [BEGIN]
    out += ['[packets.docs-md-tensix]\nname = "Docs (tensix)"\n', f"skills = {json.dumps(list(TT_PAGES))}\n\n"]
    for packet, (targets, _) in ISA.items():
        mine = [p for p in pages if p.startswith(f"docs-md-{packet}-")]
        listed = "".join(f'    "{p}",\n' for p in mine)
        out += [f'[packets.docs-md-{packet}]\nname = "Docs ({targets})"\nskills = [\n{listed}]\n\n']
    return "".join(out).rstrip("\n") + "\n" + END


def write_packets() -> None:
    text = PLUGIN.read_text()
    head, _, rest = text.partition(BEGIN)
    _, _, tail = rest.partition(END)
    PLUGIN.write_text(head + packets_block() + tail)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m alloy.hb_plugin.pages", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)  # fmt: skip
    parser.add_argument("packet", choices=["tensix", *ISA])
    parser.add_argument("tree", type=pathlib.Path, nargs="?", help="tensix: a tt-metal tree; softhier: softhier-sdk")
    args = parser.parse_args(argv)
    if args.packet == "tensix":
        if args.tree is None:
            parser.error("tensix: pass the tt-metal tree")
        built, entry = docs_pages(args.tree)
    else:
        built, entry = isa_pages(args.packet, args.tree)
        for stale in SKILLS.glob(f"docs-md-{args.packet}-*/SKILL.md"):
            stale.unlink()
            stale.parent.rmdir()
    for name, text in built.items():
        path = SKILLS / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        print(f"{path}: {len(text.encode())} bytes")
    manifest = json.loads(MANIFEST.read_text())
    manifest["rule"] = RULE
    manifest.setdefault("packets", {})[args.packet] = entry
    MANIFEST.write_text(json.dumps(manifest, indent=1) + "\n")
    write_packets()
    return 0


if __name__ == "__main__":
    sys.exit(main())
