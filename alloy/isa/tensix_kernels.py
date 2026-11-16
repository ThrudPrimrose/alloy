# Copyright 2026 ETH Zurich and the Alloy authors.
"""Which loop-level kernels the Tensix case study (A13) can run: a kernel whose canonical form (the bench's
``canon_cpu`` pipeline, what Alloy receives) is elementwise over one-dimensional arrays (each access indexes its array by the map's own parameter) and calls only operations with a
Tensix row (``tensix.toml``). Prints, per kernel, the operations it needs and the first reason it is refused.

    python -m alloy.isa.tensix_kernels [kernel ...]      # default: the whole loop-level track
"""

import ast
import sys
from collections.abc import Iterable
from dataclasses import dataclass

import dace
from dace.sdfg import nodes
from dace.sdfg.state import LoopRegion

from alloy.isa import tensix

__all__ = ["Fit", "OPERATORS", "fit", "main"]

#: Python operators and calls -> the Tensix row that computes them.
OPERATORS: dict[type | str, str] = {
    ast.Add: "add", ast.Sub: "sub", ast.Mult: "mul", ast.Div: "div", ast.USub: "neg",
    "exp": "exp", "log": "log", "sqrt": "sqrt", "abs": "abs", "fabs": "abs", "tanh": "tanh", "sin": "sin", "cos": "cos",
}  # fmt: skip


#: Casts to the kernel's own type, which a tile program needs no call for (everything runs in fp32).
CASTS = frozenset({"float32", "float", "float64", "dace.float32"})


@dataclass(frozen=True, slots=True)
class Fit:
    """A kernel's verdict: the Tensix rows it needs, and why it is refused ("" when it fits)."""

    kernel: str
    ops: tuple[str, ...]
    refused: str


def tasklet_ops(tasklet: nodes.Tasklet) -> tuple[set[str], str]:
    """The rows a Python tasklet needs, and the first construct no row computes."""
    if tasklet.language != dace.Language.Python:
        return set(), f"{tasklet.label}: a {tasklet.language.name} tasklet"
    needed: set[str] = set()
    for node in ast.walk(ast.parse(tasklet.code.as_string)):
        if isinstance(node, ast.BinOp | ast.UnaryOp) and not isinstance(node.op, ast.UAdd):
            if type(node.op) not in OPERATORS:
                return needed, f"{tasklet.label}: operator {type(node.op).__name__}"
            needed.add(OPERATORS[type(node.op)])
        elif isinstance(node, ast.Call):
            name = (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else node.func.id
                if isinstance(node.func, ast.Name)
                else ""
            )
            if name in CASTS:
                continue
            if name not in OPERATORS:
                return needed, f"{tasklet.label}: call {name}"
            needed.add(OPERATORS[name])
        elif isinstance(node, ast.Compare | ast.BoolOp | ast.IfExp | ast.If):
            return needed, f"{tasklet.label}: a condition"
    return needed, ""


def elementwise(state: dace.SDFGState, entry: nodes.MapEntry) -> str:
    """Why ``entry``'s map is not elementwise over one-dimensional arrays, or ""."""
    if len(entry.map.params) != 1:
        return f"a {len(entry.map.params)}-dimensional map"
    param = entry.map.params[0]
    edges = [*state.out_edges(entry), *state.in_edges(state.exit_node(entry))]
    for edge in edges:
        if edge.data.is_empty():
            continue
        if edge.data.wcr is not None:
            return f"an accumulation into {edge.data.data}"
        if str(edge.data.subset) != param:
            return f"{edge.data.data}[{edge.data.subset}] is not indexed by the map's {param}"
    return ""


def fit(kernel: str, sdfg: dace.SDFG, rows: frozenset[str]) -> Fit:
    """``kernel``'s verdict from its SDFG: every map elementwise and one-dimensional, no loop, every tasklet inside a
    map and computing only operations of ``rows``."""
    needed: set[str] = set()
    for block in sdfg.all_control_flow_regions(recursive=True):
        if isinstance(block, LoopRegion):
            return Fit(kernel, tuple(sorted(needed)), f"a loop ({block.label})")
    for state in [b for b in sdfg.all_control_flow_blocks(recursive=True) if isinstance(b, dace.SDFGState)]:
        scopes = state.scope_dict()
        for node in state.nodes():
            if isinstance(node, nodes.MapEntry) and (why := elementwise(state, node)):
                return Fit(kernel, tuple(sorted(needed)), why)
            if isinstance(node, nodes.NestedSDFG | nodes.LibraryNode):
                return Fit(kernel, tuple(sorted(needed)), f"{type(node).__name__} {node.label}")
            if isinstance(node, nodes.Tasklet):
                if not any(not e.data.is_empty() for e in state.all_edges(node)):
                    continue  # a size assumption check (``abort()`` on a negative length): host work, no data
                if scopes[node] is None:
                    return Fit(kernel, tuple(sorted(needed)), f"{node.label}: outside a map")
                ops, why = tasklet_ops(node)
                needed |= ops
                if why:
                    return Fit(kernel, tuple(sorted(needed)), why)
    missing = sorted(needed - rows)
    return Fit(kernel, tuple(sorted(needed)), f"no Tensix row for {', '.join(missing)}" if missing else "")


def track_kernels() -> list[str]:
    from hpcagent_bench import paths

    folder = paths.BENCHMARKS / "loop_level_reasoning"
    return sorted(d.name for d in folder.iterdir() if (d / f"{d.name}.yaml").is_file())


def kernel_sdfg(kernel: str) -> dace.SDFG:
    """The kernel as Alloy sees it: the bench's canonical CPU pipeline, at fp32 (the vector unit has no fp64)."""
    from hpcagent_bench.precision import Precision
    from hpcagent_bench.spec import BenchSpec

    from alloy.hb_plugin.adapter import pipeline_sdfg

    return pipeline_sdfg(BenchSpec.load(kernel), "canon_cpu", Precision.FP32)


def fits(kernels: Iterable[str]) -> list[Fit]:
    rows = frozenset(row.op for row in tensix.rows())
    out = []
    for kernel in kernels:
        try:
            out.append(fit(kernel, kernel_sdfg(kernel), rows))
        except Exception as exc:  # a port that does not parse is refused with its reason, not the whole run
            out.append(Fit(kernel, (), f"no SDFG: {type(exc).__name__}: {str(exc).splitlines()[0][:120]}"))
    return out


def main(argv: list[str] | None = None) -> int:
    kernels = (argv if argv is not None else sys.argv[1:]) or track_kernels()
    found = fits(kernels)
    for f in found:
        print(f"{f.kernel}\t{'fits' if not f.refused else 'refused'}\t{' '.join(f.ops)}\t{f.refused}")
    print(f"{sum(not f.refused for f in found)} of {len(found)} kernels fit", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
