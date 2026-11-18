# Copyright 2026 ETH Zurich and the Alloy authors.
"""C to NumPy: a deterministic translation of one C kernel in canonical C form into a NumPy kernel, so DaCe can parse
it and Alloy can tune it.

Canonical C form: one function; arrays as ``T *restrict`` flat row-major pointers with symbolic ``int64_t``
extents; scalars; declarations, assignments, ``for``, ``while``, ``if``, ``malloc``/``free``, ``memset``, math.h and
``cblas_?gemm``/``cblas_?gemv`` calls. Anything else is refused with the reason (:class:`Refused`).

The translation runs in three phases: :func:`lift` turns the C syntax tree (tree-sitter's C grammar) into loop-level
Python, delinearizing ``A[(i)*(N) + (j)]`` against ``A``'s shape to ``A[i, j]``; :func:`raise_idioms` rewrites loop
nests into NumPy statements (``@`` for a matrix product, whole-array statements for element-wise nests, ``np.sum``
for a reduction) and a temporary's ``np.empty`` plus its first full assignment into one assignment; :func:`emit`
prints the module.

    python -m alloy.frontend.cnumpy KERNEL.c BINDING.json   # the NumPy module on stdout
"""

import argparse
import ast
import json
import pathlib
import sys
from dataclasses import dataclass, field

import sympy

__all__ = ["Array", "Refused", "translate"]

#: C scalar types and the NumPy dtype each one holds.
DTYPES = {
    "double": "float64",
    "float": "float32",
    "int64_t": "int64",
    "int32_t": "int32",
    "int": "int32",
    "long": "int64",
    "size_t": "int64",
    "uint8_t": "uint8",
    "int8_t": "int8",
    "uint32_t": "uint32",
    "uint64_t": "uint64",
    "bool": "bool",
    "_Bool": "bool",
    "blasint": "int64",
}
#: Binding argument kinds (``ptr_double``, ``int64``, ...) to NumPy dtypes.
KINDS = {"double": "float64", "float": "float32", "int64": "int64", "int32": "int32", "bool": "bool", "uint8": "uint8"}
#: math.h functions and their NumPy spelling; the ``f`` variants map the same way.
MATH = {
    "sqrt": "np.sqrt", "exp": "np.exp", "log": "np.log", "log10": "np.log10", "log2": "np.log2", "log1p": "np.log1p",
    "expm1": "np.expm1", "exp2": "np.exp2", "sin": "np.sin", "cos": "np.cos", "tan": "np.tan", "asin": "np.arcsin",
    "acos": "np.arccos", "atan": "np.arctan", "atan2": "np.arctan2", "sinh": "np.sinh", "cosh": "np.cosh",
    "tanh": "np.tanh", "fabs": "np.abs", "floor": "np.floor", "ceil": "np.ceil", "round": "np.round",
    "trunc": "np.trunc", "pow": "np.power", "fmin": "np.minimum", "fmax": "np.maximum", "fmod": "np.fmod",
    "cbrt": "np.cbrt", "hypot": "np.hypot", "copysign": "np.copysign", "isnan": "np.isnan", "isinf": "np.isinf",
    "isfinite": "np.isfinite", "abs": "abs", "llabs": "abs", "labs": "abs", "min": "min", "max": "max",
}  # fmt: skip
CONSTANTS = {"M_PI": "np.pi", "M_E": "np.e", "INFINITY": "np.inf", "NAN": "np.nan", "true": "True", "false": "False"}
#: Statements the translation drops: allocation checks and frees have no NumPy counterpart.
DROPPED = ("free", "__npb_alloc_check")


class Refused(ValueError):
    """The C is outside canonical C form; the message names the construct and its line."""


@dataclass(slots=True)
class Array:
    """An array: its NumPy dtype and its shape as expressions over the kernel's symbols."""

    dtype: str
    shape: tuple[str, ...]


@dataclass(slots=True)
class Scope:
    """What the lifter knows while it walks the function: arrays, scalar types, the source bytes."""

    source: bytes
    arrays: dict[str, Array] = field(default_factory=dict[str, Array])
    scalars: dict[str, str] = field(default_factory=dict[str, str])
    renamed: dict[str, str] = field(default_factory=dict[str, str])


def text(scope: Scope, node) -> str:
    return scope.source[node.start_byte : node.end_byte].decode()


def refuse(scope: Scope, node, what: str) -> Refused:
    return Refused(f"line {node.start_point[0] + 1}: {what}: {text(scope, node)[:80]!r}")


def python_name(scope: Scope, name: str) -> str:
    """A C name as a canonical-NumPy name: no leading underscore, no clash with another name."""
    if name in scope.renamed:
        return scope.renamed[name]
    new = name.lstrip("_") or "v"
    taken = set(scope.renamed.values())
    while new in taken or (new != name and new in scope.arrays | scope.scalars):
        new = f"{new}_"
    scope.renamed[name] = new
    return new


# ---------------------------------------------------------------------------------------------------- symbols


def symbolic(scope: Scope, node) -> sympy.Expr | None:
    """An integer index expression as a SymPy expression, or None when it is not a polynomial in names."""
    kind = node.type
    if kind == "parenthesized_expression":
        return symbolic(scope, node.named_children[0])
    if kind == "identifier":
        return sympy.Symbol(python_name(scope, text(scope, node)), integer=True)
    if kind == "number_literal":
        value = text(scope, node).rstrip("uUlL")
        return sympy.Integer(int(value, 0)) if value.lstrip("-").isdigit() or value.startswith("0x") else None
    if kind == "cast_expression":
        return symbolic(scope, node.child_by_field_name("value"))
    if kind == "unary_expression" and text(scope, node.child_by_field_name("operator")) == "-":
        inner = symbolic(scope, node.child_by_field_name("argument"))
        return None if inner is None else -inner
    if kind == "binary_expression":
        op = text(scope, node.child_by_field_name("operator"))
        left = symbolic(scope, node.child_by_field_name("left"))
        right = symbolic(scope, node.child_by_field_name("right"))
        if left is None or right is None:
            return None
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
    return None


def shape_symbol(scope: Scope, extent: str) -> sympy.Expr:
    """A binding's extent (``"NI"``, ``"N + 1"``, ``"2*N"``) as a SymPy expression over the kernel's names."""
    names = {n.id for n in ast.walk(ast.parse(extent, mode="eval")) if isinstance(n, ast.Name)}
    return sympy.sympify(extent, locals={n: sympy.Symbol(python_name(scope, n), integer=True) for n in names})


def delinearize(scope: Scope, array: Array, index: sympy.Expr) -> list[sympy.Expr] | None:
    """``index`` into the flat row-major ``array`` as one index per dimension, or None when the terms do not split
    by the strides (the caller then indexes a flat view)."""
    shape = [shape_symbol(scope, s) for s in array.shape]
    if len(shape) <= 1:
        return [index]
    rest = sympy.expand(index)
    found = []
    for k in range(len(shape) - 1):
        stride = sympy.Mul(*shape[k + 1 :])
        taken = sympy.Integer(0)
        for term in sympy.Add.make_args(rest):
            quotient = sympy.simplify(term / stride)
            if sympy.fraction(sympy.together(quotient))[1] == 1:
                taken += quotient
        found.append(taken)
        rest = sympy.expand(rest - taken * stride)
    found.append(rest)
    return found


def printed(expr: sympy.Expr) -> str:
    return str(expr).replace(" ", "")


# ---------------------------------------------------------------------------------------------------- expressions


def c_type(scope: Scope, node) -> str:
    name = text(scope, node).replace("const", "").replace("unsigned", "").strip()
    if name not in DTYPES:
        raise refuse(scope, node, "a type outside canonical C form")
    return name


def is_integer(scope: Scope, node) -> bool:
    """Whether a C expression has an integer type (C's ``/`` and ``%`` truncate on integers)."""
    kind = node.type
    if kind == "parenthesized_expression":
        return is_integer(scope, node.named_children[0])
    if kind == "number_literal":
        value = text(scope, node).lower()
        return not any(c in value for c in ".e") or value.startswith("0x")
    if kind == "identifier":
        name = text(scope, node)
        dtype = scope.scalars.get(name) or (scope.arrays[name].dtype if name in scope.arrays else "float64")
        return dtype.startswith(("int", "uint"))
    if kind == "subscript_expression":
        name = text(scope, node.child_by_field_name("argument"))
        return name in scope.arrays and scope.arrays[name].dtype.startswith(("int", "uint"))
    if kind == "cast_expression":
        return DTYPES.get(text(scope, node.child_by_field_name("type")).strip(), "float64").startswith(("int", "uint"))
    if kind == "binary_expression":
        op = text(scope, node.child_by_field_name("operator"))
        if op in ("<", ">", "<=", ">=", "==", "!=", "&&", "||"):
            return True
        return is_integer(scope, node.child_by_field_name("left")) and is_integer(scope, node.child_by_field_name("right"))
    if kind == "unary_expression":
        return is_integer(scope, node.child_by_field_name("argument"))
    return False


def expression(scope: Scope, node) -> str:
    """A C expression as Python source."""
    kind = node.type
    if kind == "parenthesized_expression":
        return f"({expression(scope, node.named_children[0])})"
    if kind == "identifier":
        name = text(scope, node)
        return CONSTANTS.get(name) or python_name(scope, name)
    if kind in ("true", "false", "null"):
        return {"true": "True", "false": "False"}.get(kind) or "None"
    if kind == "number_literal":
        value = text(scope, node)
        lowered = value.lower()
        if lowered.startswith("0x"):
            return str(int(lowered.rstrip("ul"), 16))
        return lowered.rstrip("fl").rstrip("u").rstrip("l") if "." in lowered or "e" in lowered else lowered.rstrip("ul")
    if kind == "subscript_expression":
        return subscript(scope, node)
    if kind == "binary_expression":
        op = text(scope, node.child_by_field_name("operator"))
        left_node, right_node = node.child_by_field_name("left"), node.child_by_field_name("right")
        left, right = expression(scope, left_node), expression(scope, right_node)
        if op in ("/", "%") and is_integer(scope, left_node) and is_integer(scope, right_node):
            helper = "c_div" if op == "/" else "c_mod"
            return f"{helper}({left}, {right})"
        python = {"&&": "and", "||": "or"}.get(op, op)
        return f"({left} {python} {right})"
    if kind == "unary_expression":
        op = text(scope, node.child_by_field_name("operator"))
        argument = expression(scope, node.child_by_field_name("argument"))
        return f"(not {argument})" if op == "!" else f"({op}{argument})"
    if kind == "conditional_expression":
        test, yes, no = (expression(scope, node.child_by_field_name(f)) for f in ("condition", "consequence", "alternative"))
        return f"({yes} if {test} else {no})"
    if kind == "cast_expression":
        target = text(scope, node.child_by_field_name("type")).strip()
        value = expression(scope, node.child_by_field_name("value"))
        if target not in DTYPES:
            raise refuse(scope, node, "a cast outside canonical C form")
        return f"np.{DTYPES[target]}({value})"
    if kind == "call_expression":
        return call(scope, node)
    raise refuse(scope, node, f"an expression outside canonical C form ({kind})")


def subscript(scope: Scope, node) -> str:
    """``A[flat]`` as ``A[i, j]`` against ``A``'s shape, or as an index into its flat view."""
    base = node.child_by_field_name("argument")
    if base.type != "identifier":
        raise refuse(scope, node, "a subscript of something other than a named array")
    name = text(scope, base)
    index_node = node.child_by_field_name("index") or node.child_by_field_name("indices")
    array = scope.arrays.get(name)
    if array is None:
        raise refuse(scope, node, f"{name} is no array of the binding and no malloc'd temporary")
    target = python_name(scope, name)
    index = symbolic(scope, index_node)
    split = None if index is None else delinearize(scope, array, index)
    if split is None:
        flat = expression(scope, index_node)
        return f"{target}.reshape(-1)[{flat}]" if len(array.shape) != 1 else f"{target}[{flat}]"
    return f"{target}[{', '.join(printed(e) for e in split)}]"


def call(scope: Scope, node) -> str:
    function = text(scope, node.child_by_field_name("function"))
    arguments = [expression(scope, a) for a in node.child_by_field_name("arguments").named_children]
    base = function[:-1] if function.endswith("f") and function[:-1] in MATH else function
    if base in MATH:
        return f"{MATH[base]}({', '.join(arguments)})"
    if function == "int_floor":  # the bench's C spelling of Python's //
        return f"({arguments[0]} // {arguments[1]})"
    if function == "python_mod":  # the bench's C spelling of Python's %
        return f"({arguments[0]} % {arguments[1]})"
    raise refuse(scope, node, f"a call to {function}, which canonical C form does not know")


# ---------------------------------------------------------------------------------------------------- statements


def malloc_shape(scope: Scope, node) -> tuple[str, ...]:
    """The shape of ``malloc((size_t)((NI) * (NK)) * sizeof(T))``: the factors of its element count, in order."""
    size = node.child_by_field_name("arguments").named_children[0]
    factors: list[str] = []

    def walk(n) -> None:
        if n.type == "parenthesized_expression":
            walk(n.named_children[0])
        elif n.type == "cast_expression":
            walk(n.child_by_field_name("value"))
        elif n.type == "binary_expression" and text(scope, n.child_by_field_name("operator")) == "*":
            walk(n.child_by_field_name("left"))
            walk(n.child_by_field_name("right"))
        elif n.type != "sizeof_expression":
            factors.append(expression(scope, n))

    walk(size)
    return tuple(factors) or ("1",)


def unwrap_cast(node):
    while node is not None and node.type in ("cast_expression", "parenthesized_expression"):
        node = node.child_by_field_name("value") if node.type == "cast_expression" else node.named_children[0]
    return node


def declaration(scope: Scope, node) -> list[str]:
    ctype = c_type(scope, node.child_by_field_name("type"))
    out = []
    for declarator in node.children_by_field_name("declarator"):
        value = declarator.child_by_field_name("value") if declarator.type == "init_declarator" else None
        target = declarator.child_by_field_name("declarator") if declarator.type == "init_declarator" else declarator
        if target.type == "pointer_declarator":
            name = text(scope, target.child_by_field_name("declarator"))
            allocation = unwrap_cast(value)
            if allocation is None or allocation.type != "call_expression" or text(
                scope, allocation.child_by_field_name("function")
            ) not in ("malloc", "calloc"):
                raise refuse(scope, node, "a pointer that is not a malloc'd temporary")
            if text(scope, allocation.child_by_field_name("function")) == "calloc":
                raise refuse(scope, node, "calloc")
            shape = malloc_shape(scope, allocation)
            scope.arrays[name] = Array(DTYPES[ctype], shape)
            shape_text = f"({', '.join(shape)},)" if len(shape) == 1 else f"({', '.join(shape)})"
            out.append(f"{python_name(scope, name)} = np.empty({shape_text}, dtype=np.{DTYPES[ctype]})")
            continue
        if target.type != "identifier":
            raise refuse(scope, node, "a declarator outside canonical C form (array or function)")
        name = text(scope, target)
        scope.scalars[name] = DTYPES[ctype]
        if value is not None:
            out.append(f"{python_name(scope, name)} = {cast_to(scope, name, expression(scope, value))}")
    return out


def cast_to(scope: Scope, name: str, value: str) -> str:
    """A value stored in a ``float`` scalar stays float32, as in C."""
    return f"np.float32({value})" if scope.scalars.get(name) == "float32" else value


def assignment(scope: Scope, node) -> str:
    left, right = node.child_by_field_name("left"), node.child_by_field_name("right")
    op = text(scope, node.child_by_field_name("operator"))
    target = expression(scope, left)
    value = expression(scope, right)
    name = text(scope, left) if left.type == "identifier" else ""
    if op in ("/=", "%=") and is_integer(scope, left) and is_integer(scope, right):
        helper = "c_div" if op == "/=" else "c_mod"
        return f"{target} = {helper}({target}, {value})"
    if scope.scalars.get(name) == "float32":
        return f"{target} = {cast_to(scope, name, value if op == '=' else f'{target} {op[:-1]} {value}')}"
    return f"{target} {op} {value}"


def statement(scope: Scope, node) -> list[str]:
    """A C statement as Python lines (indentation by four spaces per level)."""
    kind = node.type
    if kind == "compound_statement":
        return [line for child in node.named_children if child.type != "comment" for line in statement(scope, child)]
    if kind == "declaration":
        return declaration(scope, node)
    if kind == "expression_statement":
        if not node.named_children:
            return []
        inner = node.named_children[0]
        if inner.type == "assignment_expression":
            return [assignment(scope, inner)]
        if inner.type == "update_expression":
            op = "+=" if "++" in text(scope, inner) else "-="
            return [f"{expression(scope, inner.child_by_field_name('argument'))} {op} 1"]
        if inner.type == "call_expression":
            return call_statement(scope, inner)
        raise refuse(scope, node, "an expression statement without effect")
    if kind == "for_statement":
        return for_loop(scope, node)
    if kind == "while_statement":
        test = expression(scope, node.child_by_field_name("condition"))
        return [f"while {test}:", *indented(statement(scope, node.child_by_field_name("body")))]
    if kind == "if_statement":
        lines = [f"if {expression(scope, node.child_by_field_name('condition'))}:"]
        lines += indented(statement(scope, node.child_by_field_name("consequence")))
        alternative = node.child_by_field_name("alternative")
        if alternative is not None:
            body = alternative.named_children[0] if alternative.type == "else_clause" else alternative
            lines += ["else:", *indented(statement(scope, body))]
        return lines
    if kind in ("break_statement", "continue_statement"):
        return [kind.split("_")[0]]
    if kind == "return_statement":
        if node.named_children:
            raise refuse(scope, node, "a returned value (the C ABI writes outputs through pointers)")
        return ["return"]
    if kind == "comment":
        return []
    raise refuse(scope, node, f"a statement outside canonical C form ({kind})")


def indented(lines: list[str]) -> list[str]:
    return [f"    {line}" for line in lines] or ["    pass"]


def for_loop(scope: Scope, node) -> list[str]:
    """``for (int64_t i = lo; i < hi; ++i)`` as ``for i in range(lo, hi)``; any other shape as a while loop."""
    init, test, update = (node.child_by_field_name(f) for f in ("initializer", "condition", "update"))
    body = node.child_by_field_name("body")
    variable = canonical_range(scope, init, test, update)
    if variable is not None:
        name, low, high, step = variable
        scope.scalars.setdefault(name, "int64")
        bounds = f"{low}, {high}" if step == "1" else f"{low}, {high}, {step}"
        return [f"for {python_name(scope, name)} in range({bounds}):", *indented(statement(scope, body))]
    if any(n.type == "continue_statement" for n in walk(body)):
        raise refuse(scope, node, "continue in a for loop without a canonical range")
    lines = [] if init is None else statement(scope, init) if init.type == "declaration" else [assignment(scope, init)]
    step = [] if update is None else statement_of_update(scope, update)
    test_text = "True" if test is None else expression(scope, test)
    return [*lines, f"while {test_text}:", *indented([*statement(scope, body), *step])]


def walk(node):
    yield node
    for child in node.named_children:
        yield from walk(child)


def statement_of_update(scope: Scope, update) -> list[str]:
    if update.type == "update_expression":
        op = "+=" if "++" in text(scope, update) else "-="
        return [f"{expression(scope, update.child_by_field_name('argument'))} {op} 1"]
    if update.type == "assignment_expression":
        return [assignment(scope, update)]
    raise refuse(scope, update, "a for-loop update outside canonical C form")


def canonical_range(scope: Scope, init, test, update) -> tuple[str, str, str, str] | None:
    """(variable, low, high, step) of a for loop over an integer range whose variable the body may read but the
    header alone advances, or None."""
    if init is None or test is None or update is None or init.type != "declaration":
        return None
    declarators = init.children_by_field_name("declarator")
    if len(declarators) != 1 or declarators[0].type != "init_declarator":
        return None
    name = text(scope, declarators[0].child_by_field_name("declarator"))
    if c_type(scope, init.child_by_field_name("type")) not in ("int64_t", "int", "int32_t", "long", "size_t"):
        return None
    scope.scalars[name] = "int64"
    low = expression(scope, declarators[0].child_by_field_name("value"))
    if test.type != "binary_expression" or text(scope, test.child_by_field_name("left")) != name:
        return None
    op = text(scope, test.child_by_field_name("operator"))
    bound = expression(scope, test.child_by_field_name("right"))
    if update.type == "update_expression" and text(scope, update.child_by_field_name("argument")) == name:
        step = "1" if "++" in text(scope, update) else "-1"
    elif update.type == "assignment_expression" and text(scope, update.child_by_field_name("left")) == name:
        amount = expression(scope, update.child_by_field_name("right"))
        op_update = text(scope, update.child_by_field_name("operator"))
        if op_update not in ("+=", "-="):
            return None
        step = amount if op_update == "+=" else f"-{amount}"
    else:
        return None
    upward = not step.startswith("-")
    if upward and op == "<":
        return name, low, bound, step
    if upward and op == "<=":
        return name, low, f"{bound} + 1", step
    if not upward and op == ">":
        return name, low, bound, step
    if not upward and op == ">=":
        return name, low, f"{bound} - 1", step
    return None


def call_statement(scope: Scope, node) -> list[str]:
    function = text(scope, node.child_by_field_name("function"))
    arguments = node.child_by_field_name("arguments").named_children
    if function in DROPPED:
        return []
    if function == "memset":
        name = text(scope, unwrap_cast(arguments[0]))
        if name not in scope.arrays or text(scope, arguments[1]).strip() != "0":
            raise refuse(scope, node, "memset of something other than an array to zero")
        return [f"{python_name(scope, name)}[...] = 0"]
    if function.startswith("cblas_") and function[6:] in ("dgemm", "sgemm"):
        return [gemm(scope, node, arguments)]
    if function.startswith("cblas_") and function[6:] in ("dgemv", "sgemv"):
        return [gemv(scope, node, arguments)]
    raise refuse(scope, node, f"a call statement to {function}, which canonical C form does not know")


def operand(scope: Scope, node, rows: str, cols: str, transposed: bool) -> str:
    """A BLAS operand as a matrix: the array (reshaped to rows x cols when its shape differs) and transposed."""
    name = text(scope, unwrap_cast(node))
    if name not in scope.arrays:
        raise refuse(scope, node, "a BLAS operand that is no array")
    array = scope.arrays[name]
    target = python_name(scope, name)
    stored = (cols, rows) if transposed else (rows, cols)
    if tuple(printed(shape_symbol(scope, s)) for s in array.shape) != tuple(
        printed(shape_symbol(scope, s)) for s in stored
    ):
        target = f"{target}.reshape(({stored[0]}, {stored[1]}))"
    return f"{target}.T" if transposed else target


def blas_scale(value: str, product: str) -> str:
    return product if value in ("1.0", "1") else f"{value} * ({product})"


def gemm(scope: Scope, node, arguments) -> str:
    """``cblas_dgemm(CblasRowMajor, ta, tb, M, N, K, alpha, A, lda, B, ldb, beta, C, ldc)`` as ``@``."""
    if len(arguments) != 14 or text(scope, arguments[0]) != "CblasRowMajor":
        raise refuse(scope, node, "a gemm call outside row-major canonical form")
    m, n, k = (expression(scope, unwrap_cast(a)) for a in arguments[3:6])
    alpha, beta = expression(scope, arguments[6]), expression(scope, arguments[11])
    a = operand(scope, arguments[7], m, k, text(scope, arguments[1]) == "CblasTrans")
    b = operand(scope, arguments[9], k, n, text(scope, arguments[2]) == "CblasTrans")
    c = operand(scope, arguments[12], m, n, False)
    product = blas_scale(alpha, f"{a} @ {b}")
    if beta in ("0.0", "0"):
        return f"{c}[...] = {product}"
    return f"{c}[...] = {product} + {blas_scale(beta, c)}"


def gemv(scope: Scope, node, arguments) -> str:
    """``cblas_dgemv(CblasRowMajor, t, M, N, alpha, A, lda, x, incx, beta, y, incy)`` as ``@``."""
    if len(arguments) != 12 or text(scope, arguments[0]) != "CblasRowMajor":
        raise refuse(scope, node, "a gemv call outside row-major canonical form")
    if text(scope, arguments[8]) != "1" or text(scope, arguments[11]) != "1":
        raise refuse(scope, node, "a strided gemv")
    m, n = (expression(scope, unwrap_cast(a)) for a in arguments[2:4])
    alpha, beta = expression(scope, arguments[4]), expression(scope, arguments[9])
    a = operand(scope, arguments[5], m, n, text(scope, arguments[1]) == "CblasTrans")
    x = python_name(scope, text(scope, unwrap_cast(arguments[7])))
    y = python_name(scope, text(scope, unwrap_cast(arguments[10])))
    product = blas_scale(alpha, f"{a} @ {x}")
    if beta in ("0.0", "0"):
        return f"{y}[...] = {product}"
    return f"{y}[...] = {product} + {blas_scale(beta, y)}"


# ---------------------------------------------------------------------------------------------------- the function


def function_node(source: bytes, name: str):
    from tree_sitter_language_pack import get_parser

    tree = get_parser("c").parse(source)
    for node in tree.root_node.named_children:
        if node.type != "function_definition":
            continue
        declarator = node.child_by_field_name("declarator")
        while declarator is not None and declarator.type != "function_declarator":
            declarator = declarator.child_by_field_name("declarator")
        if declarator is not None and source[
            declarator.child_by_field_name("declarator").start_byte : declarator.child_by_field_name("declarator").end_byte
        ].decode() == name:
            return node, declarator
    raise Refused(f"no function {name} in the source")


def lift(source: str, binding: dict) -> tuple[list[str], list[str], Scope]:
    """The kernel of ``binding`` (``kernel``, ``args`` with ``name``, ``kind``, ``shape``) as loop-level Python: its
    parameter names, its body lines, and what the lifter learned."""
    raw = source.encode()
    scope = Scope(raw)
    node, declarator = function_node(raw, binding["kernel"])
    for arg in binding["args"]:
        kind = arg["kind"]
        if kind.startswith("ptr_"):
            scope.arrays[arg["name"]] = Array(KINDS.get(kind[4:], kind[4:]), tuple(str(s) for s in arg.get("shape", [])))
        else:
            scope.scalars[arg["name"]] = KINDS.get(kind, kind)
    parameters = []
    for parameter in declarator.child_by_field_name("parameters").named_children:
        inner = parameter.child_by_field_name("declarator")
        while inner is not None and inner.type != "identifier":
            inner = inner.child_by_field_name("declarator")
        if inner is None:
            raise refuse(scope, parameter, "a parameter without a name")
        name = text(scope, inner)
        if name not in scope.arrays and name not in scope.scalars:
            raise refuse(scope, parameter, f"{name} is not in the binding")
        parameters.append(name)
    body = statement(scope, node.child_by_field_name("body"))
    return [python_name(scope, p) for p in parameters], body, scope


# ---------------------------------------------------------------------------------------------------- idioms


def full_shape(scope: Scope, name: str) -> tuple[str, ...] | None:
    original = next((c for c, p in scope.renamed.items() if p == name), name)
    array = scope.arrays.get(original)
    return None if array is None else tuple(printed(shape_symbol(scope, s)) for s in array.shape)


def range_of(loop: ast.For) -> tuple[str, str] | None:
    """(variable, extent) of ``for v in range(0, extent)`` or ``range(extent)``."""
    if not isinstance(loop.target, ast.Name) or not isinstance(loop.iter, ast.Call):
        return None
    call_node = loop.iter
    if not isinstance(call_node.func, ast.Name) or call_node.func.id != "range" or loop.orelse:
        return None
    args = call_node.args
    if len(args) == 1:
        return loop.target.id, printed(sympy.sympify(ast.unparse(args[0]), locals=symbols_of(args[0])))
    if len(args) == 2 and ast.unparse(args[0]) == "0":
        return loop.target.id, printed(sympy.sympify(ast.unparse(args[1]), locals=symbols_of(args[1])))
    return None


def symbols_of(node: ast.AST) -> dict[str, sympy.Symbol]:
    return {n.id: sympy.Symbol(n.id, integer=True) for n in ast.walk(node) if isinstance(n, ast.Name)}


def nest(loop: ast.For) -> tuple[list[tuple[str, str]], list[ast.stmt]]:
    """The perfectly nested full ranges from ``loop`` down, and the innermost body."""
    ranges = []
    body: list[ast.stmt] = [loop]
    while len(body) == 1 and isinstance(body[0], ast.For) and (r := range_of(body[0])) is not None:
        ranges.append(r)
        body = body[0].body
    return ranges, body


def index_names(node: ast.Subscript) -> tuple[str, ...] | None:
    index = node.slice
    items = index.elts if isinstance(index, ast.Tuple) else [index]
    return tuple(i.id for i in items if isinstance(i, ast.Name)) if all(isinstance(i, ast.Name) for i in items) else None


def vectorized(scope: Scope, expr: ast.expr, variables: tuple[str, ...], shape: tuple[str, ...]) -> ast.expr | None:
    """``expr`` with every ``X[v...]`` (``X`` of ``shape``) replaced by ``X``, or None when the loop variables appear
    any other way."""

    class Rewrite(ast.NodeTransformer):
        failed = False

        def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
            if isinstance(node.value, ast.Name) and index_names(node) == variables:
                if full_shape(scope, node.value.id) == shape:
                    return ast.Name(node.value.id, ast.Load())
                self.failed = True
                return node
            if {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} & set(variables):
                self.failed = True
            return node

        def visit_Name(self, node: ast.Name) -> ast.AST:
            if node.id in variables:
                self.failed = True
            return node

        def visit_IfExp(self, node: ast.IfExp) -> ast.AST:
            self.generic_visit(node)
            return call_np("where", node.test, node.body, node.orelse)

        def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
            self.generic_visit(node)
            name = "logical_and" if isinstance(node.op, ast.And) else "logical_or"
            out = node.values[0]
            for value in node.values[1:]:
                out = call_np(name, out, value)
            return out

        def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
            self.generic_visit(node)
            return call_np("logical_not", node.operand) if isinstance(node.op, ast.Not) else node

        def visit_Call(self, node: ast.Call) -> ast.AST:
            self.generic_visit(node)
            if isinstance(node.func, ast.Name) and node.func.id in ("min", "max", "abs") and not node.keywords:
                name = {"min": "minimum", "max": "maximum", "abs": "abs"}[node.func.id]
                return call_np(name, *node.args)
            if isinstance(node.func, ast.Name):  # c_div, c_mod
                self.failed = True
            return node

    rewrite = Rewrite()
    out = rewrite.visit(ast.parse(ast.unparse(expr), mode="eval").body)
    return None if rewrite.failed else out


def call_np(name: str, *args: ast.expr) -> ast.Call:
    return ast.Call(ast.Attribute(ast.Name("np", ast.Load()), name, ast.Load()), list(args), [])


def whole(name: str) -> ast.Subscript:
    return ast.Subscript(ast.Name(name, ast.Load()), ast.Constant(Ellipsis), ast.Store())


def elementwise(scope: Scope, loop: ast.For) -> ast.stmt | None:
    """A full-range nest whose one statement writes ``X[v...]`` and reads arrays only at ``[v...]``, as one
    whole-array statement."""
    ranges, body = nest(loop)
    if not ranges or len(body) != 1 or not isinstance(body[0], (ast.Assign, ast.AugAssign)):
        return None
    stmt = body[0]
    target = stmt.targets[0] if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 else getattr(stmt, "target", None)
    variables = tuple(v for v, _ in ranges)
    shape = tuple(e for _, e in ranges)
    if not isinstance(target, ast.Subscript) or not isinstance(target.value, ast.Name):
        return None
    if index_names(target) != variables or full_shape(scope, target.value.id) != shape:
        return None
    value = vectorized(scope, stmt.value, variables, shape)
    if value is None:
        return None
    if isinstance(stmt, ast.AugAssign):
        return ast.AugAssign(whole(target.value.id), stmt.op, value)
    return ast.Assign([whole(target.value.id)], value)


def product_operand(scope: Scope, node: ast.expr, rows: str, cols: str) -> tuple[str, str] | None:
    """(spelling, inner) of a matrix product operand ``X[r, c]`` over loop variables: ``X`` or ``X.T``."""
    if not isinstance(node, ast.Subscript) or not isinstance(node.value, ast.Name):
        return None
    names = index_names(node)
    if names is None or len(names) != 2:
        return None
    return node.value.id, ",".join(names)


def matmul(scope: Scope, loop: ast.For) -> list[ast.stmt] | None:
    """``for i: for j: X[i, j] = 0; for l: X[i, j] += Y[i, l] * Z[l, j]`` as ``X[...] = Y @ Z`` (transposes too);
    without the zero, as ``X[...] += Y @ Z``."""
    outer, body = nest(loop)
    if len(outer) != 2:
        return None
    (i, m), (j, n) = outer
    init = None
    if len(body) == 2 and isinstance(body[0], ast.Assign):
        init, body = body[0], body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.For):
        return None
    inner = range_of(body[0])
    if inner is None or len(body[0].body) != 1 or not isinstance(body[0].body[0], ast.AugAssign):
        return None
    l, k = inner
    update = body[0].body[0]
    target = update.target
    if not (isinstance(update.op, ast.Add) and isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)):
        return None
    if index_names(target) != (i, j) or full_shape(scope, target.value.id) != (m, n):
        return None
    if init is not None and not (
        len(init.targets) == 1
        and ast.dump(init.targets[0]) == ast.dump(ast.Subscript(target.value, target.slice, ast.Store()))
        and isinstance(init.value, ast.Constant)
        and init.value.value == 0
    ):
        return None
    product = update.value
    if not (isinstance(product, ast.BinOp) and isinstance(product.op, ast.Mult)):
        return None
    spelled = []
    for side, (rows, cols) in ((product.left, (m, k)), (product.right, (k, n))):
        if not isinstance(side, ast.Subscript) or not isinstance(side.value, ast.Name):
            return None
        names = index_names(side)
        shape = full_shape(scope, side.value.id)
        want = (i, l) if rows == m else (l, j)
        if names == want and shape == (rows, cols):
            spelled.append(side.value.id)
        elif names == want[::-1] and shape == (cols, rows):
            spelled.append(f"{side.value.id}.T")
        else:
            return None
    value = ast.parse(f"{spelled[0]} @ {spelled[1]}", mode="eval").body
    if init is not None:
        return [ast.Assign([whole(target.value.id)], value)]
    return [ast.AugAssign(whole(target.value.id), ast.Add(), value)]


def reduction(scope: Scope, loop: ast.For) -> ast.stmt | None:
    """``for v...: s += e[v...]`` into a scalar ``s`` as ``s += np.sum(e)``."""
    ranges, body = nest(loop)
    if not ranges or len(body) != 1 or not isinstance(body[0], ast.AugAssign):
        return None
    stmt = body[0]
    if not isinstance(stmt.target, ast.Name) or not isinstance(stmt.op, ast.Add):
        return None
    variables = tuple(v for v, _ in ranges)
    shape = tuple(e for _, e in ranges)
    value = vectorized(scope, stmt.value, variables, shape)
    if value is None or not any(isinstance(n, ast.Name) and full_shape(scope, n.id) == shape for n in ast.walk(value)):
        return None
    return ast.AugAssign(ast.Name(stmt.target.id, ast.Store()), ast.Add(), call_np("sum", value))


class Raise(ast.NodeTransformer):
    """Every loop nest that matches an idiom, innermost statements first."""

    def __init__(self, scope: Scope) -> None:
        self.scope = scope

    def visit_For(self, node: ast.For) -> ast.AST | list[ast.stmt]:
        for idiom in (matmul,):
            found = idiom(self.scope, node)
            if found is not None:
                return found
        for single in (elementwise, reduction):
            one = single(self.scope, node)
            if one is not None:
                return one
        self.generic_visit(node)
        return node


def fold_temporaries(scope: Scope, body: list[ast.stmt]) -> list[ast.stmt]:
    """``t = np.empty(...)`` whose next use writes all of ``t`` from an expression that makes a new array of ``t``'s
    shape and dtype, as one ``t = expression``."""
    out: list[ast.stmt | None] = []
    pending: dict[str, int] = {}
    for stmt in body:
        if (
            isinstance(stmt, ast.Assign)
            and isinstance(stmt.targets[0], ast.Name)
            and isinstance(stmt.value, ast.Call)
            and ast.unparse(stmt.value.func) == "np.empty"
        ):
            pending[stmt.targets[0].id] = len(out)
            out.append(stmt)
            continue
        used = {n.id for n in ast.walk(stmt) if isinstance(n, ast.Name)}
        folded = False
        for name in [n for n in pending if n in used]:
            position = pending.pop(name)
            if (
                isinstance(stmt, ast.Assign)
                and ast.unparse(stmt.targets[0]) == f"{name}[...]"
                and name not in {n.id for n in ast.walk(stmt.value) if isinstance(n, ast.Name)}
                and makes_new(scope, stmt.value, name)
            ):
                out[position] = None  # the declaration goes; the assignment stays where its inputs exist
                out.append(ast.Assign([ast.Name(name, ast.Store())], stmt.value))
                folded = True
        if not folded:
            out.append(stmt)
    return [stmt for stmt in out if stmt is not None]


def makes_new(scope: Scope, value: ast.expr, name: str) -> bool:
    """Whether ``value`` is a fresh array of ``name``'s shape and dtype: a product or element-wise arithmetic over an
    array of exactly that shape and dtype (never a bare view of another array)."""
    if not isinstance(value, (ast.BinOp, ast.UnaryOp, ast.Call)):
        return False
    shape = full_shape(scope, name)
    original = next((c for c, p in scope.renamed.items() if p == name), name)
    dtype = scope.arrays[original].dtype
    for node in ast.walk(value):
        if isinstance(node, ast.Name) and node.id != name and full_shape(scope, node.id) == shape:
            other = next((c for c, p in scope.renamed.items() if p == node.id), node.id)
            if scope.arrays[other].dtype == dtype:
                return True
    if isinstance(value, ast.BinOp) and isinstance(value.op, ast.MatMult):
        return all(scope.arrays.get(n.id, Array("", ())).dtype in (dtype, "") for n in ast.walk(value) if isinstance(n, ast.Name))
    return False


def raise_idioms(scope: Scope, body: list[str]) -> list[ast.stmt]:
    tree = ast.parse("\n".join(body) or "pass")
    tree = Raise(scope).visit(tree)
    ast.fix_missing_locations(tree)
    return fold_temporaries(scope, tree.body)


# ---------------------------------------------------------------------------------------------------- module

HELPERS = '''

def c_div(a, b):
    """C's integer division: the quotient truncated toward zero."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def c_mod(a, b):
    """C's integer remainder: the sign of the dividend."""
    return a - b * c_div(a, b)
'''


def emit(name: str, parameters: list[str], body: list[ast.stmt], scope: Scope) -> str:
    """The NumPy module: extents that an array's shape gives are read from it instead of passed."""
    given: dict[str, str] = {}
    for original, array in scope.arrays.items():
        python = python_name(scope, original)
        if python not in parameters:
            continue
        for axis, extent in enumerate(array.shape):
            if extent in parameters and extent not in given:
                given[python_name(scope, extent)] = f"{python}.shape[{axis}]"
    kept = [p for p in parameters if p not in given]
    lines = [f"{n} = {v}" for n, v in given.items()]
    function = ast.parse(f"def {name}({', '.join(kept)}):\n    pass").body[0]
    assert isinstance(function, ast.FunctionDef)
    function.body = [*ast.parse("\n".join(lines)).body, *body] or [ast.Pass()]
    source = ast.unparse(ast.fix_missing_locations(ast.Module([function], [])))
    helpers = HELPERS if "c_div(" in source or "c_mod(" in source else ""
    return f"import numpy as np\n{helpers}\n\n{source}\n"


def translate(source: str, binding: dict, name: str = "kernel") -> str:
    """The NumPy module of the C kernel ``binding["kernel"]`` in ``source``; raises :class:`Refused` outside
    canonical C form."""
    parameters, body, scope = lift(source, binding)
    return emit(name, parameters, raise_idioms(scope, body), scope)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m alloy.frontend.cnumpy", description=__doc__)
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("binding", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        print(translate(args.source.read_text(), json.loads(args.binding.read_text())), end="")
    except Refused as why:
        print(f"refused: {why}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
