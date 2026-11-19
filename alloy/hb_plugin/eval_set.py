# Copyright 2026 ETH Zurich and the Alloy authors.
"""The agent study's Tensix tasks: every bench kernel the fixed host contract can run, as a program over whole arrays.

A kernel is admitted when its canonical NumPy form is a sequence of full-range loop nests whose statements write
``X[i, j, ...]`` from reads at the same index (the nest's own variables, in order), using only operations the Tensix
table holds, or reduce such an expression into one value (``acc = acc + e`` or ``acc = max(acc, e)``); it reads at
most three input arrays (an output read in place counts) and writes one. The task keeps the bench's input domains and
scalars; :data:`TOOL_OPS` names the operations, so the host evaluates one program in torch (the float64 reference)
and in ttnn (the stock-op baseline). ``python -m alloy.hb_plugin.eval_set`` prints the admitted tasks as JSON."""

import ast
import contextlib
import dataclasses
import json
import math
import pathlib
import random
import re
import sys
from collections.abc import Callable, Iterator

import hpcagent_bench
from hpcagent_bench.cpf.cache import Target
from hpcagent_bench.precision import Precision
from hpcagent_bench.spec import KERNELS, BenchSpec
from hpcagent_bench.support.distributions.domain import RawDomain
from hpcagent_bench.support.distributions.domain import parse as parse_domain
from hpcagent_bench.tags import resolve as resolve_tag

__all__ = ["DEV", "Task", "admit", "admitted", "draw", "main", "pool"]

#: The kernels the tool was built and debugged on (design review F13): never in the eval set.
DEV = frozenset({"fuse_diamond", "tsvc_2_s451", "transc_log_wide"})
#: Calls an element expression may make, by the name the task program spells (the Tensix table's unary ops).
CALLS = {"exp": "exp", "log": "log", "sqrt": "sqrt", "sin": "sin", "cos": "cos", "tanh": "tanh", "abs": "abs",
         "fabs": "abs"}  # fmt: skip
BINOPS = {ast.Add: "+", ast.Sub: "-", ast.Mult: "*", ast.Div: "/"}
#: The bench's default input range when a kernel declares none (its fuzz default).
DEFAULT_DOMAIN = (0.0, 1.0)
MAX_INPUTS = 3
BENCHMARKS = pathlib.Path(hpcagent_bench.__file__).parent / "benchmarks"


class Refused(ValueError):
    """The kernel does not fit the host contract; the message says where."""


@dataclasses.dataclass(slots=True, frozen=True)
class Task:
    """One admitted kernel: its input arrays with their domains, its output, and its program (``name = expression``
    lines over whole arrays; ``sum(e)`` and ``max(e)`` reduce to one value)."""

    name: str
    kind: str  # "map" or "reduce"
    inputs: tuple[tuple[str, float, float], ...]
    output: str
    program: tuple[str, ...]


def element(e: ast.expr, index: list[str], scalars: dict[str, float], arrays: set[str]) -> str:
    """``e`` as a whole-array expression: ``X[i, j]`` at the nest's own index becomes ``X``."""
    if isinstance(e, ast.Constant) and isinstance(e.value, int | float) and not isinstance(e.value, bool):
        return repr(float(e.value))
    if isinstance(e, ast.Subscript) and isinstance(e.value, ast.Name):
        names = e.slice.elts if isinstance(e.slice, ast.Tuple) else [e.slice]
        if [n.id if isinstance(n, ast.Name) else None for n in names] != index:
            raise Refused(f"{ast.unparse(e)}: an access not at the nest's index {index}")
        arrays.add(e.value.id)
        return e.value.id
    if isinstance(e, ast.BinOp) and type(e.op) in BINOPS:
        left, right = element(e.left, index, scalars, arrays), element(e.right, index, scalars, arrays)
        return f"({left} {BINOPS[type(e.op)]} {right})"
    if isinstance(e, ast.UnaryOp) and isinstance(e.op, ast.USub):
        return f"(-{element(e.operand, index, scalars, arrays)})"
    if isinstance(e, ast.Call) and len(e.args) == 1 and not e.keywords:
        func = e.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
        if name in CALLS:
            return f"{CALLS[name]}({element(e.args[0], index, scalars, arrays)})"
    if isinstance(e, ast.Name) and e.id in scalars:
        return repr(scalars[e.id])
    if isinstance(e, ast.Name) and not index:  # a whole array in a whole-array statement
        arrays.add(e.id)
        return e.id
    if isinstance(e, ast.Subscript) and isinstance(e.value, ast.Name) and not index and ast.unparse(e.slice) == ":":
        arrays.add(e.value.id)
        return e.value.id
    raise Refused(f"{ast.unparse(e)}: not an element expression of the Tensix table")


def full_range(loop: ast.For, extents: dict[str, str]) -> str:
    """The loop variable of a loop over a whole axis, forward or reversed; records the axis bound."""
    if not (isinstance(loop.target, ast.Name) and isinstance(loop.iter, ast.Call) and not loop.orelse):
        raise Refused(f"line {loop.lineno}: not a plain range loop")
    func, args = loop.iter.func, [ast.unparse(a) for a in loop.iter.args]
    if not isinstance(func, ast.Name) or func.id != "range":
        raise Refused(f"line {loop.lineno}: not a range loop")
    if len(args) == 3 and args[0] == "0" and args[2] == "1":
        args = args[:2]
    if len(args) == 1 or (len(args) == 2 and args[0] == "0"):
        bound = args[-1]
    elif len(args) == 3 and args[1:] == ["-1", "-1"] and args[0].endswith(" - 1"):
        bound = args[0].removesuffix(" - 1")
    else:
        raise Refused(f"line {loop.lineno}: range({', '.join(args)}) does not cover a whole axis")
    extents[loop.target.id] = bound
    return loop.target.id


def nest(loop: ast.For, extents: dict[str, str]) -> tuple[list[str], list[ast.stmt]]:
    index, body = [full_range(loop, extents)], loop.body
    while len(body) == 1 and isinstance(body[0], ast.For):
        index.append(full_range(body[0], extents))
        body = body[0].body
    return index, body


def accumulator(target: ast.expr) -> str | None:
    """``s`` or ``out[0]``: a scalar accumulator."""
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and ast.unparse(target.slice) == "0":
        return target.value.id
    return None


def reduction(st: ast.Assign, acc: str, index: list[str], scalars: dict[str, float], arrays: set[str]) -> str:
    """``acc = acc + e`` as ``sum(e)``, ``acc = max(acc, e)`` as ``max(e)``."""
    value = st.value
    terms: list[ast.expr] = []
    while isinstance(value, ast.BinOp) and isinstance(value.op, ast.Add):  # acc + t1 + t2 nests to the left
        terms.insert(0, value.right)
        value = value.left
    if terms and accumulator(value) == acc:
        added = " + ".join(element(t, index, scalars, arrays) for t in terms)
        return f"sum({added})" if len(terms) == 1 else f"sum(({added}))"
    value = st.value
    if (isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "max"
            and len(value.args) == 2 and accumulator(value.args[0]) == acc):  # fmt: skip
        return f"max({element(value.args[1], index, scalars, arrays)})"
    raise Refused(f"line {st.lineno}: {ast.unparse(st)} is not a sum or max into {acc}")


def plain(st: ast.stmt) -> ast.stmt:
    """``x op= e`` as ``x = x op e``."""
    if isinstance(st, ast.AugAssign):
        read = ast.Name(st.target.id) if isinstance(st.target, ast.Name) else st.target
        return ast.copy_location(ast.Assign([st.target], ast.BinOp(read, st.op, st.value)), st)
    if isinstance(st, ast.For):
        st.body = [plain(b) for b in st.body]
    return st


class Indexed(ast.NodeTransformer):
    """Every use of a loop body's scalar temporaries as an element at the nest's index."""

    def __init__(self, temps: set[str], index: list[str]) -> None:
        self.temps, self.index = temps, index

    def visit_Name(self, node: ast.Name) -> ast.expr:
        if node.id not in self.temps:
            return node
        names: list[ast.expr] = [ast.Name(i) for i in self.index]
        at = names[0] if len(names) == 1 else ast.Tuple(names)
        return ast.copy_location(ast.Subscript(ast.Name(node.id), at, node.ctx), node)


def per_element(body: list[ast.stmt], index: list[str], zeroed: set[str]) -> list[ast.stmt]:
    """``body`` with each scalar it assigns (not an accumulator) made an array over the nest."""
    temps = {
        b.targets[0].id
        for b in body
        if isinstance(b, ast.Assign) and isinstance(b.targets[0], ast.Name) and b.targets[0].id not in zeroed
    }
    return [Indexed(temps, index).visit(b) for b in body] if temps else body


RETURNED = "out"


def statements(fn: ast.FunctionDef, scalars: dict[str, float]) -> Iterator[tuple[str, str, set[str], bool]]:
    """(target, expression, arrays read, reduces) per statement of the program."""
    zeroed: set[str] = set()
    for st in map(plain, fn.body):
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Constant):
            continue  # the docstring
        if isinstance(st, ast.Assign) and len(st.targets) == 1:
            target, value = st.targets[0], st.value
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Attribute) and value.func.attr == "empty":
                continue  # a temporary's allocation
            acc = accumulator(target)
            if acc is not None and isinstance(value, ast.Constant):
                zeroed.add(acc)  # the accumulator's start
                continue
            if isinstance(target, ast.Subscript) and acc is not None and isinstance(value, ast.Name):
                yield acc, value.id, {value.id}, False  # out[0] = s
                continue
            if isinstance(target, ast.Name) or (isinstance(target, ast.Subscript) and ast.unparse(target.slice) == ":"):
                arrays = set[str]()
                name = target.id if isinstance(target, ast.Name) else element(target, [], scalars, set())
                yield name, element(value, [], scalars, arrays), arrays, False  # a whole-array statement
                continue
        if isinstance(st, ast.Return) and st.value is not None:
            arrays = set[str]()
            yield RETURNED, element(st.value, [], scalars, arrays), arrays, False
            continue
        if not isinstance(st, ast.For):
            raise Refused(f"line {st.lineno}: {ast.unparse(st).splitlines()[0]} is neither a loop nest nor setup")
        extents: dict[str, str] = {}
        index, body = nest(st, extents)
        body = per_element(body, index, zeroed)
        for inner in body:
            if not (isinstance(inner, ast.Assign) and len(inner.targets) == 1):
                raise Refused(f"line {inner.lineno}: not one assignment")
            target, arrays = inner.targets[0], set[str]()
            acc = accumulator(target)
            if acc is not None and acc in zeroed:
                yield acc, reduction(inner, acc, index, scalars, arrays), arrays, True
                continue
            name = element(target, index, scalars, set())
            yield name, element(inner.value, index, scalars, arrays), arrays, False


def module_constants(module: ast.Module) -> dict[str, float]:
    """The module's numeric constants (``TMELT = 273.15``)."""
    constants = {}
    for st in module.body:
        if (isinstance(st, ast.Assign) and len(st.targets) == 1 and isinstance(st.targets[0], ast.Name)
                and isinstance(st.value, ast.Constant) and isinstance(st.value.value, int | float)):  # fmt: skip
            constants[st.targets[0].id] = float(st.value.value)
    return constants


def shape_of(task: Task) -> str:
    """The task's program and domains with its inputs renamed in order and every target by its position: equal for
    two kernels the card cannot tell apart (an in-place output included)."""
    lines = []
    for line in task.program:
        target, expression = line.split(" = ", 1)
        for i, (name, *_) in enumerate(task.inputs):
            expression = re.sub(rf"\b{re.escape(name)}\b", f"@{i}", expression)
        lines.append((target, expression))
    for k, (target, _) in enumerate(lines):
        lines = [(t, re.sub(rf"\b{re.escape(target)}\b", f"%{k}", e)) for t, e in lines]
    return f"{task.kind} {[(lo, hi) for _, lo, hi in task.inputs]} {' | '.join(e for _, e in lines)}"


def without_copies(program: list[str]) -> list[str]:
    """``s = e; out = s`` as ``out = e``: a temporary copied into the output once."""
    out: list[str] = []
    for line in program:
        target, expression = line.split(" = ", 1)
        if out and expression == out[-1].split(" = ", 1)[0]:
            out[-1] = f"{target} = {out[-1].split(' = ', 1)[1]}"
            continue
        out.append(line)
    return out


def interval(raw: RawDomain) -> tuple[float, float]:
    """A manifest domain as the range the host draws from: a sign domain or none at all is the default range, mirrored
    for a negative one."""
    domain = parse_domain(raw)
    if isinstance(domain, tuple):
        if not all(math.isfinite(v) for v in domain):
            raise Refused(f"the unbounded input domain {domain}")
        return domain
    low, high = DEFAULT_DOMAIN
    return (-high, -low) if domain in ("negative", "nonpos") else DEFAULT_DOMAIN


def admit(name: str) -> Task:
    """The task of bench kernel ``name``, or :class:`Refused` with where it leaves the host contract."""
    spec = BenchSpec.load(name)
    source = BENCHMARKS / spec.relative_path / f"{spec.module_name}_numpy.py"
    module = ast.parse(source.read_text())
    fn = next((n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == spec.func_name), None)
    if fn is None:
        raise Refused(f"no function {spec.func_name} in the NumPy form")
    init = spec.init
    scalars = module_constants(module)
    scalars |= {k: float(v) for k, v in (init.scalars if init else {}).items() if isinstance(v, int | float)}
    program, written, read, reduces = [], set[str](), set[str](), False
    for target, expression, arrays, reduced in statements(fn, scalars):
        read |= arrays - written  # an array read before this program writes it is an input
        written.add(target)
        reduces |= reduced
        program.append(f"{target} = {expression}")
    outputs = written & {*spec.array_args, RETURNED}
    if len(outputs) != 1:
        raise Refused(f"writes {len(outputs)} arrays, the contract one")
    inputs = sorted(read & set(spec.array_args))
    if not 1 <= len(inputs) <= MAX_INPUTS:
        raise Refused(f"reads {len(inputs)} arrays, the contract one to {MAX_INPUTS}")
    domains = init.domains if init else {}
    bounds = tuple((a, *interval(domains.get(a))) for a in inputs)
    kind = "reduce" if reduces else "map"
    return Task(spec.short_name, kind, bounds, outputs.pop(), tuple(without_copies(program)))


def admitted() -> tuple[list[Task], dict[str, str]]:
    """Every admitted bench kernel but the dev ones and the duplicates of an earlier one, and why each other kernel was
    refused."""
    tasks, refused, shapes = [], {}, dict[str, str]()
    for name in KERNELS:
        short = name.rsplit("/", 1)[-1]
        if short in DEV:
            refused[short] = "dev kernel"
            continue
        try:
            task = admit(name)
        except (Refused, SyntaxError, OSError) as err:
            refused[short] = str(err)
            continue
        if (first := shapes.setdefault(shape_of(task), task.name)) != task.name:
            refused[short] = f"the same program as {first}"
            continue
        tasks.append(task)
    return tasks, refused


#: The CPU and GPU agent tasks are drawn from the studies' kernels (design review F1); ML joins at the freeze, and the
#: draw aims for about 100 tasks per target (owner, 11-19: 20 is too few for a comparison).
POOL_TAGS = ("llr40", "scicomp40", "ml40")
DRAW_COUNT = 100
#: The draw's seed, fixed at the freeze: a run that redraws gets the same tasks.
DRAW_SEED = "ics27-eval"
TARGETS = {"cpu": ("canon_cpu", Target.CPU), "gpu": ("canon_gpu", Target.GPU)}


def pool() -> list[str]:
    """The kernels of :data:`POOL_TAGS`, sorted, without the dev kernels."""
    names = {name for tag in POOL_TAGS for name in resolve_tag(tag)}
    return sorted(name for name in names if name.rsplit("/", 1)[-1] not in DEV)


def alloy_takes(name: str, target: str) -> bool:
    """Whether the bench's pipeline for ``target`` builds the kernel and, on the CPU, Alloy outlines a scope of it."""
    from alloy import configuration_matrix
    from alloy.hb_plugin.adapter import nothing_to_generate, pipeline_sdfg

    pipeline, where = TARGETS[target]
    try:
        with contextlib.redirect_stdout(sys.stderr):  # DaCe's parser reports on stdout, where the draw is printed
            sdfg = pipeline_sdfg(BenchSpec.load(name), pipeline, Precision.FP64, where)
    except Exception:  # a kernel the bench's pipeline cannot build for this target is not drawn
        return False
    return target == "gpu" or not nothing_to_generate(sdfg, configuration_matrix.load())


def draw(target: str, count: int, keep: Callable[[str], bool]) -> list[str]:
    """The first ``count`` kernels of the pool, in the order a :data:`DRAW_SEED` shuffle gives, that ``keep`` takes."""
    order = pool()
    random.Random(f"{DRAW_SEED}-{target}").shuffle(order)
    drawn: list[str] = []
    for name in order:
        if len(drawn) == count:
            break
        if keep(name):
            drawn.append(name)
    return drawn


def main(argv: list[str] | None = None) -> int:
    """``eval_set`` prints the Tensix tasks as JSON; ``eval_set draw cpu|gpu [N]`` the drawn kernels, one per line."""
    args = sys.argv[1:] if argv is None else argv
    if args[:1] == ["draw"]:
        target, count = args[1], int(args[2]) if len(args) > 2 else DRAW_COUNT
        print("\n".join(draw(target, count, lambda name: alloy_takes(name, target))))
        return 0
    tasks, _ = admitted()
    json.dump([dataclasses.asdict(t) for t in tasks], sys.stdout, indent=1)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
