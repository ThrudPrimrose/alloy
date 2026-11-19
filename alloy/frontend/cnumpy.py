# Copyright 2026 ETH Zurich and the Alloy authors.
"""C to NumPy: a deterministic translation of one C kernel in canonical C form into a NumPy kernel, so DaCe can parse
it and Alloy can tune it.

Canonical C form: one function; arrays as ``T *restrict`` flat row-major pointers with symbolic ``int64_t`` extents;
scalars; declarations (local arrays and ``malloc``'d temporaries too), assignments, ``for``, ``while``, ``do``, ``if``,
``free``, ``memset``, ``memcpy``, math.h, ``cblas_?gemm``/``?gemv``/``?dot``, and file-scope constants. Anything else
is refused with the reason (:class:`Refused`); ``alloy/hb_plugin/skills/alloy-c/SKILL.md`` lists them.

The parse is tree-sitter's C grammar: it reads GNU and C23 C (``constexpr``, ``_Generic`` in the bench's prelude)
without a preprocessor, where pycparser needs preprocessed C89/C99. The translation runs in three phases: :func:`lift`
turns the syntax tree into loop-level Python, delinearizing ``A[(i)*(N) + (j)]`` against ``A``'s shape to
``A[i, j]``; :func:`raise_idioms` rewrites loop nests into NumPy statements (``@`` for a matrix product, whole-array
statements for element-wise nests, ``np.sum`` for reductions); :func:`emit` prints the module in the bench's
canonical NumPy form.

    python -m alloy.frontend.cnumpy KERNEL.c BINDING.json [--out kernel.py] [--sdfg kernel.sdfg]
"""

import argparse
import ast
import importlib.util
import json
import keyword
import pathlib
import re
import sys
import tempfile
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import sympy
from tree_sitter import Node

if TYPE_CHECKING:
    import dace

__all__ = ["Array", "Lifted", "Refused", "lift", "python_identifier", "to_sdfg", "translate"]

#: C scalar types and the NumPy dtype each one holds.
DTYPES = {
    "double": "float64",
    "float": "float32",
    "int64_t": "int64",
    "int32_t": "int32",
    "int16_t": "int16",
    "int8_t": "int8",
    "uint64_t": "uint64",
    "uint32_t": "uint32",
    "uint16_t": "uint16",
    "uint8_t": "uint8",
    "int": "int32",
    "signed": "int32",
    "signed int": "int32",
    "unsigned": "uint32",
    "unsigned int": "uint32",
    "long": "int64",
    "long int": "int64",
    "long long": "int64",
    "long long int": "int64",
    "unsigned long": "uint64",
    "unsigned long long": "uint64",
    "short": "int16",
    "unsigned short": "uint16",
    "char": "int8",
    "signed char": "int8",
    "unsigned char": "uint8",
    # shortcut: size_t is signed here so index arithmetic never mixes uint64 and int64, upgrade if a kernel wraps one
    "size_t": "int64",
    "ptrdiff_t": "int64",
    "ssize_t": "int64",
    "bool": "bool",
    "_Bool": "bool",
    "blasint": "int64",
}
#: Binding argument kinds (``ptr_double``, ``int64``, ...) to NumPy dtypes.
KINDS = {
    "double": "float64",
    "float": "float32",
    "int64": "int64",
    "int32": "int32",
    "int16": "int16",
    "int8": "int8",
    "uint64": "uint64",
    "uint32": "uint32",
    "uint16": "uint16",
    "uint8": "uint8",
    "bool": "bool",
}
#: math.h functions and their NumPy spelling; the ``f`` variants map the same way.
MATH = {
    "sqrt": "np.sqrt", "exp": "np.exp", "log": "np.log", "log10": "np.log10", "log2": "np.log2", "log1p": "np.log1p",
    "expm1": "np.expm1", "exp2": "np.exp2", "sin": "np.sin", "cos": "np.cos", "tan": "np.tan", "asin": "np.arcsin",
    "acos": "np.arccos", "atan": "np.arctan", "atan2": "np.arctan2", "sinh": "np.sinh", "cosh": "np.cosh",
    "tanh": "np.tanh", "asinh": "np.arcsinh", "acosh": "np.arccosh", "atanh": "np.arctanh", "fabs": "np.abs",
    "floor": "np.floor", "ceil": "np.ceil", "trunc": "np.trunc", "fmin": "np.fmin", "fmax": "np.fmax",
    "fmod": "np.fmod", "cbrt": "np.cbrt", "hypot": "np.hypot", "copysign": "np.copysign", "isnan": "np.isnan",
    "isinf": "np.isinf", "isfinite": "np.isfinite", "abs": "np.abs", "llabs": "np.abs", "labs": "np.abs",
    "rint": "np.rint", "nearbyint": "np.rint",
    # the bench's prelude: NaN-propagating min/max and sign
    "min": "np.minimum", "max": "np.maximum", "__npb_fmax": "np.maximum", "__npb_fmin": "np.minimum",
    "__npb_fmax_f": "np.maximum", "__npb_fmin_f": "np.minimum", "__npb_fmax_i": "np.maximum",
    "__npb_fmin_i": "np.minimum", "__npb_fmax_u": "np.maximum", "__npb_fmin_u": "np.minimum",
    "__npb_sign": "np.sign",
}  # fmt: skip
#: Calls spelled as Python operators: name -> template over the arguments ``{0}``, ``{1}``.
OPERATORS = {
    "int_floor": "({0} // {1})",
    "floord": "({0} // {1})",
    "__npb_floordiv_i": "({0} // {1})",
    "__npb_floordiv_f": "({0} // {1})",
    "__npb_floordiv_u": "({0} // {1})",
    "int_ceil": "(-((-{0}) // {1}))",
    "ceild": "(-((-{0}) // {1}))",
    "__npb_ceildiv_i": "(-((-{0}) // {1}))",
    "__npb_ceildiv_f": "(-((-{0}) // {1}))",
    "__npb_ceildiv_u": "(-((-{0}) // {1}))",
    "python_mod": "({0} % {1})",
    "python_fmod": "({0} % {1})",
    "__npb_mod_i": "({0} % {1})",
    "__npb_mod_u": "({0} % {1})",
    "__npb_int_pow": "({0} ** {1})",
    "pow": "np.power(np.float64({0}), {1})",
    "powf": "np.power(np.float32({0}), np.float32({1}))",
    "round": "np.copysign(np.floor(np.abs({0}) + 0.5), {0})",
    "roundf": "np.copysign(np.floor(np.abs({0}) + np.float32(0.5)), {0})",
}
#: Calls whose result is an integer when their arguments are.
INTEGER_CALLS = frozenset(
    {"int_floor", "floord", "int_ceil", "ceild", "python_mod", "abs", "llabs", "labs", "min", "max", "__npb_int_pow"}
)
CONSTANTS = {
    "M_PI": "np.pi", "M_E": "np.e", "M_PI_2": "(np.pi / 2)", "M_PI_4": "(np.pi / 4)", "M_1_PI": "(1 / np.pi)",
    "M_2_PI": "(2 / np.pi)", "M_SQRT2": "np.sqrt(2.0)", "M_SQRT1_2": "np.sqrt(0.5)", "M_LN2": "np.log(2.0)",
    "M_LN10": "np.log(10.0)", "INFINITY": "np.inf", "HUGE_VAL": "np.inf", "NAN": "np.nan",
    "DBL_MAX": "1.7976931348623157e308", "DBL_MIN": "2.2250738585072014e-308", "DBL_EPSILON": "2.220446049250313e-16",
    "FLT_MAX": "3.4028234663852886e38", "FLT_MIN": "1.1754943508222875e-38", "FLT_EPSILON": "1.1920928955078125e-07",
    "INT64_MAX": "9223372036854775807", "INT64_MIN": "(-9223372036854775808)", "INT32_MAX": "2147483647",
    "INT32_MIN": "(-2147483648)", "INT_MAX": "2147483647", "INT_MIN": "(-2147483648)",
    "LLONG_MAX": "9223372036854775807", "LLONG_MIN": "(-9223372036854775808)",
}  # fmt: skip
INTEGER_CONSTANTS = frozenset(
    {"INT64_MAX", "INT64_MIN", "INT32_MAX", "INT32_MIN", "INT_MAX", "INT_MIN", "LLONG_MAX", "LLONG_MIN"}
)
#: Calls the translation drops: allocation checks and frees have no NumPy counterpart.
DROPPED = frozenset({"free", "__npb_alloc_check"})
#: Names the emitted module defines or reads, which a C name must not shadow.
RESERVED = frozenset({"np", "range", "abs", "min", "max", "c_div", "c_mod", "kernel", "dace", "True", "False", "None"})
INTEGER_TYPES = ("int", "uint")
COMPLEX_CALLS = frozenset({"cabs", "creal", "cimag", "conj", "cexp", "carg", "csqrt", "__npb_conj"})


class Refused(ValueError):
    """The C is outside canonical C form: ``reason`` names the construct, the message adds its line and text."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


@dataclass(slots=True)
class Array:
    """An array: its NumPy dtype and its shape as Python expressions over the kernel's names."""

    dtype: str
    shape: tuple[str, ...]
    #: Indexed with one subscript per axis (``t[i][j]``, a local C array), not through a flat index.
    nested: bool = False


@dataclass(slots=True)
class Scope:
    """What the lifter knows while it walks the kernel: arrays, scalar types, names proven non-negative."""

    source: bytes
    arrays: dict[str, Array] = field(default_factory=dict[str, Array])
    scalars: dict[str, str] = field(default_factory=dict[str, str])
    #: Pointers declared without storage yet (``double *t = NULL;``): C name -> dtype.
    pointers: dict[str, str] = field(default_factory=dict[str, str])
    renamed: dict[str, str] = field(default_factory=dict[str, str])
    nonnegative: set[str] = field(default_factory=set[str])
    #: Python spelling of opaque index terms: symbol name -> source.
    opaque: dict[str, str] = field(default_factory=dict[str, str])
    #: File-scope constants: C name -> (Python literal, dtype).
    constants: dict[str, tuple[str, str]] = field(default_factory=dict[str, tuple[str, str]])
    #: The constants the kernel reads.
    used: set[str] = field(default_factory=set[str])
    #: Every function the file defines: C name -> definition.
    functions: dict[str, Node] = field(default_factory=dict[str, Node])


@dataclass(slots=True)
class Lifted:
    """The kernel as loop-level Python: its parameter names (Python spelling), body lines, and what the lifter
    learned."""

    parameters: list[str]
    body: list[str]
    scope: Scope


def text(scope: Scope, node: Node) -> str:
    return scope.source[node.start_byte : node.end_byte].decode()


def refuse(scope: Scope, node: Node, what: str) -> Refused:
    return Refused(what, f"line {node.start_point[0] + 1}: {text(scope, node)[:80]!r}")


def child(scope: Scope, node: Node, name: str) -> Node:
    """The child ``name`` of ``node``; its absence is outside canonical C form."""
    found = node.child_by_field_name(name)
    if found is None:
        raise refuse(scope, node, f"a {node.type} without its {name}")
    return found


def python_identifier(name: str) -> str:
    """A C name as a Python name: no leading underscore, no keyword, no name the module itself uses."""
    new = name.lstrip("_") or "v"
    return f"{new}_" if keyword.iskeyword(new) or new in RESERVED else new


def python_name(scope: Scope, name: str) -> str:
    """A C name as the kernel's Python name: :func:`python_identifier`, made unique."""
    if name in scope.renamed:
        return scope.renamed[name]
    new = python_identifier(name)
    taken = set(scope.renamed.values()) | {python_identifier(c) for c in scope.constants}
    while new in taken:
        new = f"{new}_"
    scope.renamed[name] = new
    return new


def walk(node: Node) -> Iterator[Node]:
    yield node
    for inner in node.named_children:
        yield from walk(inner)


def is_integer_dtype(dtype: str) -> bool:
    return dtype.startswith(INTEGER_TYPES)


def type_name(scope: Scope, node: Node) -> str:
    return " ".join(text(scope, node).split())


# ---------------------------------------------------------------------------------------------------- symbols


def symbolic(scope: Scope, node: Node) -> sympy.Expr:
    """An integer index expression as a SymPy polynomial; a term that is no polynomial in names (a subscript, a
    division) becomes an opaque symbol that :func:`printed` spells back."""
    kind = node.type
    if kind == "parenthesized_expression":
        return symbolic(scope, node.named_children[0])
    if kind == "identifier" and text(scope, node) in scope.constants:
        if is_integer_dtype(scope.constants[text(scope, node)][1]):
            scope.used.add(text(scope, node))  # a symbol, as the shapes name it
            return sympy.Symbol(python_identifier(text(scope, node)), integer=True)
    elif kind == "identifier" and text(scope, node) not in CONSTANTS:
        known(scope, node)
        return sympy.Symbol(python_name(scope, text(scope, node)), integer=True)
    if kind == "number_literal" and is_integer(scope, node):
        return sympy.Integer(int(number(scope, node)))
    if kind == "cast_expression" and is_integer(scope, node) and is_integer(scope, child(scope, node, "value")):
        return symbolic(scope, child(scope, node, "value"))
    if kind == "unary_expression" and text(scope, child(scope, node, "operator")) in ("-", "+"):
        inner = symbolic(scope, child(scope, node, "argument"))
        return -inner if text(scope, child(scope, node, "operator")) == "-" else inner
    if kind == "binary_expression" and text(scope, child(scope, node, "operator")) in ("+", "-", "*"):
        op = text(scope, child(scope, node, "operator"))
        left = symbolic(scope, child(scope, node, "left"))
        right = symbolic(scope, child(scope, node, "right"))
        return left + right if op == "+" else left - right if op == "-" else left * right
    spelled = expression(scope, node)
    for name, source in scope.opaque.items():
        if source == spelled:
            return sympy.Symbol(name, integer=True)
    name = f"opaque{len(scope.opaque)}x"
    scope.opaque[name] = spelled
    return sympy.Symbol(name, integer=True)


def printed(scope: Scope, expr: sympy.Expr) -> str:
    out = str(expr).replace(" ", "")
    for name, source in scope.opaque.items():
        out = out.replace(name, f"({source})")  # opaque<k>x: no name is a prefix of another
    return out


def extent(value: str) -> sympy.Expr:
    """An extent (``"NI"``, ``"N + 1"``, ``"2*N"``, Python spelling) as a SymPy expression."""
    names = {n.id for n in ast.walk(ast.parse(value, mode="eval")) if isinstance(n, ast.Name)}
    local: dict[str, Any] = {n: sympy.Symbol(n, integer=True) for n in names}
    expr = sympy.parse_expr(value.replace("//", "/"), local_dict=local)
    assert isinstance(expr, sympy.Expr)
    return expr


def row_major(scope: Scope, node: Node, shape: tuple[str, ...]) -> list[sympy.Expr] | None:
    """The indices of a flat index written in Horner form, ``((i)*(E1) + (j))*(E2) + (k)`` with each ``E`` equal to
    the extent of its axis, or None when it is not written so."""
    while node.type == "parenthesized_expression":
        node = node.named_children[0]
    if len(shape) == 1:
        return [symbolic(scope, node)]
    if node.type != "binary_expression" or text(scope, child(scope, node, "operator")) != "+":
        return None
    product = child(scope, node, "left")
    while product.type == "parenthesized_expression":
        product = product.named_children[0]
    if product.type != "binary_expression" or text(scope, child(scope, product, "operator")) != "*":
        return None
    stride = symbolic(scope, child(scope, product, "right"))
    if sympy.simplify(stride - extent(shape[-1])) != 0:
        return None
    outer = row_major(scope, child(scope, product, "left"), shape[:-1])
    return None if outer is None else [*outer, symbolic(scope, child(scope, node, "right"))]


def delinearize(array: Array, index: sympy.Expr) -> list[sympy.Expr]:
    """``index`` into the flat row-major ``array`` as one index per dimension: the terms each stride divides go to
    its dimension, what remains to the last.

    shortcut: assumes each recovered index stays inside its extent (true for C lowered from NumPy indices), upgrade
    with a bounds proof if hand C walks across rows through one flat index."""
    shape = [extent(s) for s in array.shape]
    rest = sympy.expand(index)
    found: list[sympy.Expr] = []
    for k in range(len(shape) - 1):
        stride = sympy.Mul(*shape[k + 1 :])
        taken: sympy.Expr = sympy.Integer(0)
        for term in sympy.Add.make_args(rest):
            quotient = sympy.cancel(term / stride)
            if sympy.fraction(quotient)[1] == 1:
                taken += quotient
        found.append(taken)
        rest = sympy.expand(rest - taken * stride)
    found.append(rest)
    return found


# ---------------------------------------------------------------------------------------------------- types


def c_type(scope: Scope, node: Node) -> str:
    """The NumPy dtype of a C type node."""
    name = type_name(scope, node)
    if name not in DTYPES:
        raise refuse(scope, node, "a type outside canonical C form (a struct, complex or library type)")
    return DTYPES[name]


def is_integer(scope: Scope, node: Node) -> bool:
    """Whether a C expression has an integer type (C's ``/`` and ``%`` truncate on integers)."""
    kind = node.type
    if kind == "parenthesized_expression":
        return is_integer(scope, node.named_children[0])
    if kind == "number_literal":
        value = text(scope, node).lower()
        return value.startswith("0x") or not any(c in value for c in ".e")
    if kind in ("char_literal", "true", "false"):
        return True
    if kind == "identifier":
        name = text(scope, node)
        if name in scope.constants:
            return is_integer_dtype(scope.constants[name][1])
        return name in INTEGER_CONSTANTS or is_integer_dtype(scope.scalars.get(name, "float64"))
    if kind == "pointer_expression":
        name = text(scope, child(scope, node, "argument"))
        return name in scope.arrays and is_integer_dtype(scope.arrays[name].dtype)
    if kind == "subscript_expression":
        base = node
        while base.type == "subscript_expression":
            base = child(scope, base, "argument")
        name = text(scope, base)
        return name in scope.arrays and is_integer_dtype(scope.arrays[name].dtype)
    if kind == "cast_expression":
        return is_integer_dtype(DTYPES.get(type_name(scope, child(scope, node, "type")), "float64"))
    if kind == "binary_expression":
        op = text(scope, child(scope, node, "operator"))
        if op in ("<", ">", "<=", ">=", "==", "!=", "&&", "||", "<<", ">>", "&", "|", "^"):
            return True
        return is_integer(scope, child(scope, node, "left")) and is_integer(scope, child(scope, node, "right"))
    if kind == "unary_expression":
        return text(scope, child(scope, node, "operator")) == "!" or is_integer(scope, child(scope, node, "argument"))
    if kind == "conditional_expression":
        return is_integer(scope, child(scope, node, "consequence")) and is_integer(
            scope, child(scope, node, "alternative")
        )
    if kind == "call_expression":
        function = text(scope, child(scope, node, "function"))
        if function.startswith("(") and function.strip("() ") in DTYPES:
            return is_integer_dtype(DTYPES[function.strip("() ")])
        integer_call = function in INTEGER_CALLS or function.startswith(("__npb_f", "__npb_ceildiv", "__npb_mod"))
        return integer_call and all(is_integer(scope, a) for a in arguments_of(scope, node))
    return False


def is_nonnegative(scope: Scope, node: Node) -> bool:
    """Whether an integer expression is provably non-negative (then C's ``/`` and ``%`` are Python's)."""
    kind = node.type
    if kind == "parenthesized_expression":
        return is_nonnegative(scope, node.named_children[0])
    if kind == "number_literal":
        return is_integer(scope, node)
    if kind == "identifier":
        name = text(scope, node)
        if name in scope.constants:
            return not scope.constants[name][0].startswith("-")
        return name in scope.nonnegative
    if kind == "cast_expression":
        return is_nonnegative(scope, child(scope, node, "value"))
    if kind == "binary_expression" and text(scope, child(scope, node, "operator")) in ("+", "*", "/", "%", ">>"):
        return is_nonnegative(scope, child(scope, node, "left")) and is_nonnegative(scope, child(scope, node, "right"))
    return False


# ---------------------------------------------------------------------------------------------------- expressions


def known(scope: Scope, node: Node) -> None:
    """Refuse a name that is no array, scalar or constant of the kernel."""
    name = text(scope, node)
    if name in scope.pointers:
        raise refuse(scope, node, "a pointer read before it holds a malloc'd array")
    if not (name in scope.arrays or name in scope.scalars or name in scope.constants or name in CONSTANTS):
        raise refuse(scope, node, "a name that is no array, scalar or constant (a global or a macro)")


def number(scope: Scope, node: Node) -> str:
    value = text(scope, node).lower().replace("'", "")
    if value.startswith("0x") and is_integer(scope, node):
        return str(int(value.rstrip("ul"), 16))
    if "p" in value or value.startswith("0x"):
        raise refuse(scope, node, "a hexadecimal floating literal")
    if is_integer(scope, node):
        digits = value.rstrip("ul")
        return str(int(digits, 8)) if len(digits) > 1 and digits.startswith("0") else digits
    return value.rstrip("fl")


def expression(scope: Scope, node: Node) -> str:
    """A C expression as Python source."""
    kind = node.type
    if kind == "parenthesized_expression":
        return f"({expression(scope, node.named_children[0])})"
    if kind == "identifier":
        name = text(scope, node)
        if name in scope.constants:
            scope.used.add(name)
            return python_identifier(name)
        if name in CONSTANTS:
            return CONSTANTS[name]
        known(scope, node)
        return python_name(scope, name)
    if kind in ("true", "false"):
        return "True" if kind == "true" else "False"
    if kind == "number_literal":
        return number(scope, node)
    if kind == "char_literal":
        return str(ord(text(scope, node)[1:-1].encode().decode("unicode_escape")))
    if kind == "subscript_expression":
        return subscript(scope, node)
    if kind == "binary_expression":
        return binary(scope, node)
    if kind == "unary_expression":
        op = text(scope, child(scope, node, "operator"))
        argument = expression(scope, child(scope, node, "argument"))
        return f"(not {argument})" if op == "!" else f"({op}{argument})"
    if kind == "conditional_expression":
        test, yes, no = (expression(scope, child(scope, node, f)) for f in ("condition", "consequence", "alternative"))
        return f"({yes} if {test} else {no})"
    if kind == "cast_expression":
        dtype = DTYPES.get(type_name(scope, child(scope, node, "type")), "")
        return cast(scope, node, child(scope, node, "value"), dtype)
    if kind == "call_expression":
        return call(scope, node)
    if kind == "gnu_asm_expression":
        raise refuse(scope, node, "inline asm")
    if kind == "pointer_expression":
        return dereference(scope, node)
    if kind in ("update_expression", "assignment_expression", "comma_expression"):
        raise refuse(scope, node, "an assignment inside an expression")
    if kind == "sizeof_expression":
        raise refuse(scope, node, "sizeof outside an allocation")
    if kind in ("field_expression", "compound_literal_expression", "initializer_list"):
        raise refuse(scope, node, "a struct or union")
    raise refuse(scope, node, f"an expression outside canonical C form ({kind})")


def dereference(scope: Scope, node: Node) -> str:
    """``*p`` of an array ``p`` as ``p[0]``; any other pointer expression is pointer arithmetic."""
    argument = child(scope, node, "argument")
    name = text(scope, argument)
    if text(scope, child(scope, node, "operator")) != "*" or argument.type != "identifier" or name not in scope.arrays:
        raise refuse(scope, node, "a pointer dereference or address (pointer arithmetic)")
    return f"{python_name(scope, name)}[{', '.join('0' * len(scope.arrays[name].shape))}]"


def binary(scope: Scope, node: Node) -> str:
    op = text(scope, child(scope, node, "operator"))
    left_node, right_node = child(scope, node, "left"), child(scope, node, "right")
    left, right = expression(scope, left_node), expression(scope, right_node)
    if op in ("/", "%") and is_integer(scope, left_node) and is_integer(scope, right_node):
        if is_nonnegative(scope, left_node) and is_nonnegative(scope, right_node):
            return f"({left} {'//' if op == '/' else '%'} {right})"
        return f"{'c_div' if op == '/' else 'c_mod'}({left}, {right})"
    return f"({left} {ast_operator(op)} {right})"


def ast_operator(op: str) -> str:
    return {"&&": "and", "||": "or"}.get(op, op)


def cast(scope: Scope, node: Node, value_node: Node, dtype: str) -> str:
    """``(T)value``: dropped where the value already has ``T``'s kind at full width, else a NumPy scalar cast."""
    if not dtype:
        raise refuse(scope, node, "a cast outside canonical C form (a pointer or struct type)")
    value = expression(scope, value_node)
    integer = is_integer(scope, value_node)
    if dtype == "int64" and integer or dtype == "float64" and not integer:
        return value
    return f"np.{dtype}({value})"


def subscript(scope: Scope, node: Node) -> str:
    """``A[flat]`` as ``A[i, j]`` against ``A``'s shape; ``t[i][j]`` of a local array as ``t[i, j]``."""
    indices: list[Node] = []
    base = node
    while base.type == "subscript_expression":
        indices.insert(0, child(scope, base, "index"))
        base = child(scope, base, "argument")
    if base.type != "identifier":
        raise refuse(scope, node, "a subscript of something other than a named array")
    name = text(scope, base)
    if name in scope.pointers:
        raise refuse(scope, node, "a pointer read before it holds a malloc'd array")
    array = scope.arrays.get(name)
    if array is None:
        raise refuse(scope, node, "a subscript of a name that is no array of the binding and no temporary")
    target = python_name(scope, name)
    if array.nested or len(indices) > 1:
        if len(indices) != len(array.shape):
            raise refuse(scope, node, "a partial subscript of a multidimensional array")
        return f"{target}[{', '.join(expression(scope, i) for i in indices)}]"
    if len(array.shape) == 1:
        return f"{target}[{expression(scope, indices[0])}]"
    split = row_major(scope, indices[0], array.shape)
    if split is None and any(not (e.is_Symbol or e.is_Integer) for e in map(extent, array.shape[1:])):
        return f"{target}.reshape(-1)[{expression(scope, indices[0])}]"  # strides split only against names
    split = split or delinearize(array, symbolic(scope, indices[0]))
    return f"{target}[{', '.join(printed(scope, e) for e in split)}]"


def arguments_of(scope: Scope, node: Node) -> list[Node]:
    return [a for a in child(scope, node, "arguments").named_children if a.type != "comment"]


def call(scope: Scope, node: Node) -> str:
    function_node = child(scope, node, "function")
    function = text(scope, function_node)
    arguments = arguments_of(scope, node)
    if function_node.type == "parenthesized_expression" and function.strip("() ") in DTYPES:
        if len(arguments) != 1:
            raise refuse(scope, node, "an assignment inside an expression")
        return cast(scope, node, arguments[0], DTYPES[function.strip("() ")])  # (blasint)(n) parses as a call
    if function_node.type != "identifier":
        raise refuse(scope, node, "a call through a function pointer")
    if function in COMPLEX_CALLS:
        raise refuse(scope, node, "complex arithmetic")
    if function in ("cblas_ddot", "cblas_sdot"):
        return dot(scope, node, arguments)
    base = function[:-1] if function.endswith("f") and function[:-1] in MATH else function
    if function in OPERATORS:
        return OPERATORS[function].format(*(expression(scope, a) for a in arguments))
    if base in MATH and (function.startswith("__npb_") or function not in scope.functions or base in ("min", "max")):
        return f"{MATH[base]}({', '.join(expression(scope, a) for a in arguments)})"
    if function in scope.functions:
        raise refuse(scope, node, "a call to a helper function of the file (inline it into the kernel)")
    raise refuse(scope, node, "a call to a function outside math.h and BLAS")


# ---------------------------------------------------------------------------------------------------- statements


def factors(scope: Scope, node: Node) -> list[str]:
    """The axes of an element count such as ``(size_t)(((K)) * ((M + 1))) * sizeof(T)``: the operands of its
    products, a parenthesized operand one axis, ``sizeof`` dropped. A cast's own parentheses are no axis."""
    if node.type == "cast_expression":
        value = child(scope, node, "value")
        inner = value.named_children[0] if value.type == "parenthesized_expression" else value
        return [expression(scope, inner)] if inner.type == "parenthesized_expression" else factors(scope, inner)
    if node.type == "parenthesized_expression" and any(n.type == "sizeof_expression" for n in walk(node)):
        return factors(scope, node.named_children[0])
    if node.type == "binary_expression" and text(scope, child(scope, node, "operator")) == "*":
        return factors(scope, child(scope, node, "left")) + factors(scope, child(scope, node, "right"))
    if node.type == "sizeof_expression":
        return []
    return [expression(scope, node)]


def unwrap_cast(node: Node | None) -> Node | None:
    while node is not None and node.type in ("cast_expression", "parenthesized_expression"):
        node = node.child_by_field_name("value") if node.type == "cast_expression" else node.named_children[0]
    return node


def shape_text(shape: tuple[str, ...]) -> str:
    return f"({shape[0]},)" if len(shape) == 1 else f"({', '.join(shape)})"


def pointer_value(scope: Scope, node: Node, name: str, dtype: str, value: Node | None) -> list[str]:
    """A pointer variable set to ``value``: nothing yet (``NULL``), new storage (``malloc``, ``calloc``), or
    another array of the same type."""
    inner = unwrap_cast(value)
    if inner is None or inner.type == "null" or inner.type == "number_literal" and text(scope, inner) == "0":
        if name not in scope.arrays:
            scope.pointers[name] = dtype
        return []
    function = text(scope, child(scope, inner, "function")) if inner.type == "call_expression" else ""
    if function in ("malloc", "calloc"):
        arguments = arguments_of(scope, inner)
        if len(arguments) != (1 if function == "malloc" else 2):
            raise refuse(scope, node, "an allocation outside malloc(count * sizeof(T)) and calloc(count, size)")
        shape = tuple(f for a in arguments for f in factors(scope, a)) or ("1",)
        scope.pointers.pop(name, None)
        scope.arrays[name] = Array(dtype, shape)
        maker = "zeros" if function == "calloc" else "empty"
        return [f"{python_name(scope, name)} = np.{maker}({shape_text(shape)}, dtype=np.{dtype})"]
    if inner.type == "identifier" and text(scope, inner) in scope.arrays:
        other = scope.arrays[text(scope, inner)]
        if other.dtype != dtype:
            raise refuse(scope, node, "a pointer of another type over an array")
        scope.pointers.pop(name, None)
        scope.arrays[name] = Array(other.dtype, other.shape, other.nested)
        return [f"{python_name(scope, name)} = {python_name(scope, text(scope, inner))}"]
    raise refuse(scope, node, "a pointer into an array (pointer arithmetic)")


def local_array(scope: Scope, node: Node, declarator: Node, dtype: str, value: Node | None) -> list[str]:
    """``T t[N][M]`` (optionally ``= {0}`` or a literal list) as ``np.empty`` or ``np.zeros``."""
    shape: list[str] = []
    inner = declarator
    while inner.type == "array_declarator":
        shape.insert(0, expression(scope, child(scope, inner, "size")))
        inner = child(scope, inner, "declarator")
    name = text(scope, inner)
    scope.arrays[name] = Array(dtype, tuple(shape), nested=True)
    target = python_name(scope, name)
    if value is None:
        return [f"{target} = np.empty({shape_text(tuple(shape))}, dtype=np.{dtype})"]
    if value.type != "initializer_list" or any(v.type == "initializer_list" for v in value.named_children):
        raise refuse(scope, node, "an array initializer other than a flat literal list")
    items = [expression(scope, v) for v in value.named_children if v.type != "comment"]
    zeros = f"{target} = np.zeros({shape_text(tuple(shape))}, dtype=np.{dtype})"
    if all(v in ("0", "0.0") for v in items):
        return [zeros]
    if len(shape) != 1:
        raise refuse(scope, node, "an array initializer other than a flat literal list")
    return [zeros, f"{target}[0:{len(items)}] = np.array([{', '.join(items)}], dtype=np.{dtype})"]


def declaration(scope: Scope, node: Node) -> list[str]:
    dtype = c_type(scope, child(scope, node, "type"))
    out: list[str] = []
    for declarator in node.children_by_field_name("declarator"):
        value = declarator.child_by_field_name("value") if declarator.type == "init_declarator" else None
        target = child(scope, declarator, "declarator") if declarator.type == "init_declarator" else declarator
        if target.type == "pointer_declarator":
            inner = child(scope, target, "declarator")
            if inner.type != "identifier":
                raise refuse(scope, node, "a pointer to a pointer")
            out += pointer_value(scope, node, text(scope, inner), dtype, value)
        elif target.type == "array_declarator":
            out += local_array(scope, node, target, dtype, value)
        elif target.type != "identifier":
            raise refuse(scope, node, "a declarator outside canonical C form (a function or struct)")
        else:
            name = text(scope, target)
            scope.scalars[name] = dtype
            scope.nonnegative.discard(name)
            if value is not None:
                out.append(f"{python_name(scope, name)} = {stored(scope, name, value, expression(scope, value))}")
    return out


def stored(scope: Scope, name: str, value: Node, spelled: str) -> str:
    """The value a C scalar of ``name``'s type holds after the store: float32 and narrow integers keep their width,
    an integer truncates a float."""
    dtype = scope.scalars.get(name, "float64")
    if dtype in ("float32", "bool") or is_integer_dtype(dtype) and (dtype != "int64" or not is_integer(scope, value)):
        return f"np.{dtype}({spelled})"
    return spelled


def assignment(scope: Scope, node: Node) -> list[str]:
    left, right = child(scope, node, "left"), child(scope, node, "right")
    op = text(scope, child(scope, node, "operator"))
    if left.type == "identifier" and (text(scope, left) in scope.arrays or text(scope, left) in scope.pointers):
        if op != "=":
            raise refuse(scope, node, "a pointer into an array (pointer arithmetic)")
        name = text(scope, left)
        dtype = scope.arrays[name].dtype if name in scope.arrays else scope.pointers[name]
        return pointer_value(scope, node, name, dtype, right)
    if left.type not in ("identifier", "subscript_expression", "pointer_expression"):
        raise refuse(scope, node, "a store through something other than a name or a subscript")
    target, value = expression(scope, left), expression(scope, right)
    name = text(scope, left) if left.type == "identifier" else ""
    scope.nonnegative.discard(name)
    if op in ("/=", "%=") and is_integer(scope, left) and is_integer(scope, right):
        python = f"{'c_div' if op == '/=' else 'c_mod'}({target}, {value})"
        if is_nonnegative(scope, left) and is_nonnegative(scope, right):
            python = f"({target} {'//' if op == '/=' else '%'} {value})"
        return [f"{target} = {stored(scope, name, right, python) if name else python}"]
    if name and stored(scope, name, right, "v") != "v":
        combined = value if op == "=" else f"{target} {op[:-1]} ({value})"
        return [f"{target} = {stored(scope, name, right, combined)}"]
    return [f"{target} {op} {value}"]


def statement(scope: Scope, node: Node) -> list[str]:
    """A C statement as Python lines (four spaces per level)."""
    kind = node.type
    if kind == "compound_statement":
        return [line for inner in node.named_children for line in statement(scope, inner)]
    if kind == "declaration":
        return declaration(scope, node)
    if kind == "expression_statement":
        if not node.named_children:
            return []
        inner = node.named_children[0]
        if inner.type == "assignment_expression":
            return assignment(scope, inner)
        if inner.type == "update_expression":
            return update(scope, inner)
        if inner.type == "call_expression":
            return call_statement(scope, inner)
        if inner.type == "gnu_asm_expression":
            raise refuse(scope, node, "inline asm")
        raise refuse(scope, node, "an expression statement without effect (or a comma expression)")
    if kind == "for_statement":
        return for_loop(scope, node)
    if kind == "while_statement":
        test = expression(scope, child(scope, node, "condition"))
        return [f"while {test}:", *indented(statement(scope, child(scope, node, "body")))]
    if kind == "do_statement":
        body = child(scope, node, "body")
        if any(n.type == "continue_statement" for n in loop_body_nodes(body)):
            raise refuse(scope, node, "continue in a loop without a canonical range")
        test = expression(scope, child(scope, node, "condition"))
        return ["while True:", *indented([*statement(scope, body), f"if not {test}:", "    break"])]
    if kind == "if_statement":
        return if_statement(scope, node)
    if kind in ("break_statement", "continue_statement"):
        return [kind.split("_")[0]]
    if kind == "return_statement":
        if node.named_children:
            raise refuse(scope, node, "a returned value (the C ABI writes outputs through pointers)")
        return ["return"]
    if kind in ("comment", "empty_statement") or kind == "preproc_call" and text(scope, node).startswith("#pragma"):
        return []
    if kind in ("goto_statement", "labeled_statement"):
        raise refuse(scope, node, "goto")
    if kind == "switch_statement":
        raise refuse(scope, node, "switch")
    raise refuse(scope, node, f"a statement outside canonical C form ({kind})")


def if_statement(scope: Scope, node: Node) -> list[str]:
    condition = child(scope, node, "condition")
    inner = unwrap_cast(condition)
    names = [text(scope, n) for n in walk(condition) if n.type == "identifier"]
    nulls = any(n.type == "null" for n in walk(condition)) or inner is not None and inner.type == "unary_expression"
    if nulls and names and all(n in scope.arrays or n in scope.pointers for n in names):
        return []  # if (!p) or if (p == NULL): the allocation check, which NumPy raises instead
    lines = [f"if {expression(scope, condition)}:", *indented(statement(scope, child(scope, node, "consequence")))]
    alternative = node.child_by_field_name("alternative")
    if alternative is not None:
        body = alternative.named_children[0] if alternative.type == "else_clause" else alternative
        lines += ["else:", *indented(statement(scope, body))]
    return lines


def update(scope: Scope, node: Node) -> list[str]:
    argument = child(scope, node, "argument")
    if argument.type == "identifier" and text(scope, argument) in scope.arrays:
        raise refuse(scope, node, "a pointer into an array (pointer arithmetic)")
    target = expression(scope, argument)
    op = "+" if "++" in text(scope, node) else "-"
    name = text(scope, argument) if argument.type == "identifier" else ""
    scope.nonnegative.discard(name)
    if name and stored(scope, name, argument, "v") != "v":
        return [f"{target} = {stored(scope, name, argument, f'{target} {op} 1')}"]
    return [f"{target} {op}= 1"]


def indented(lines: list[str]) -> list[str]:
    return [f"    {line}" for line in lines] or ["    pass"]


def loop_body_nodes(body: Node) -> Iterator[Node]:
    """The nodes of a loop body outside nested loops (where ``continue`` binds to this loop)."""
    yield body
    for inner in body.named_children:
        if inner.type not in ("for_statement", "while_statement", "do_statement"):
            yield from loop_body_nodes(inner)


def stored_names(scope: Scope, node: Node) -> set[str]:
    """The names a statement stores to (assignment or increment targets)."""
    names: set[str] = set()
    for n in walk(node):
        target = None
        if n.type == "assignment_expression":
            target = n.child_by_field_name("left")
        elif n.type == "update_expression":
            target = n.child_by_field_name("argument")
        if target is not None and target.type == "identifier":
            names.add(text(scope, target))
    return names


def for_loop(scope: Scope, node: Node) -> list[str]:
    """``for (int64_t i = lo; i < hi; ++i)`` as ``for i in range(lo, hi)``; any other shape as a while loop."""
    init, test, step = (node.child_by_field_name(f) for f in ("initializer", "condition", "update"))
    body = child(scope, node, "body")
    found = canonical_range(scope, init, test, step, body)
    if found is not None:
        name, bounds, nonnegative = found
        if nonnegative:
            scope.nonnegative.add(name)
        lines = [f"for {python_name(scope, name)} in range({bounds}):", *indented(statement(scope, body))]
        scope.nonnegative.discard(name)
        return lines
    if any(n.type == "continue_statement" for n in loop_body_nodes(body)):
        raise refuse(scope, node, "continue in a loop without a canonical range")
    first: list[str] = []
    if init is not None and init.type == "declaration":
        first = declaration(scope, init)
    elif init is not None and init.type == "assignment_expression":
        first = assignment(scope, init)
    elif init is not None:
        raise refuse(scope, init, "a for-loop header outside canonical C form")
    for name in stored_names(scope, node):
        scope.nonnegative.discard(name)
    advance: list[str] = []
    if step is not None and step.type == "update_expression":
        advance = update(scope, step)
    elif step is not None and step.type == "assignment_expression":
        advance = assignment(scope, step)
    elif step is not None:
        raise refuse(scope, step, "a for-loop header outside canonical C form")
    test_text = "True" if test is None else expression(scope, test)
    return [*first, f"while {test_text}:", *indented([*statement(scope, body), *advance])]


def canonical_range(
    scope: Scope, init: Node | None, test: Node | None, step: Node | None, body: Node
) -> tuple[str, str, bool] | None:
    """(variable, range arguments, non-negative) of a for loop over an integer range whose header alone advances
    its variable and whose bound the body leaves alone, or None."""
    if init is None or test is None or step is None or init.type != "declaration":
        return None
    declarators = init.children_by_field_name("declarator")
    if len(declarators) != 1 or declarators[0].type != "init_declarator":
        return None
    variable = child(scope, declarators[0], "declarator")
    if variable.type != "identifier" or not is_integer_dtype(c_type(scope, child(scope, init, "type"))):
        return None
    name = text(scope, variable)
    if test.type != "binary_expression" or text(scope, child(scope, test, "left")) != name:
        return None
    bound = child(scope, test, "right")
    written = stored_names(scope, body)
    if name in written or {text(scope, n) for n in walk(bound) if n.type == "identifier"} & written:
        return None
    if any(n.type in ("call_expression", "assignment_expression", "update_expression") for n in walk(bound)):
        return None
    amount = "1"
    if step.type == "update_expression" and text(scope, child(scope, step, "argument")) == name:
        upward = "++" in text(scope, step)
    elif step.type == "assignment_expression" and text(scope, child(scope, step, "left")) == name:
        operator, right = text(scope, child(scope, step, "operator")), child(scope, step, "right")
        if operator not in ("+=", "-=") or right.type != "number_literal" or not is_integer(scope, right):
            return None
        upward, amount = operator == "+=", number(scope, right)
    else:
        return None
    value = child(scope, declarators[0], "value")
    scope.scalars[name] = "int64"
    low, high = expression(scope, value), expression(scope, bound)
    op = text(scope, child(scope, test, "operator"))
    stride = "" if amount == "1" and upward else f", {amount if upward else '-' + amount}"
    if upward and op in ("<", "<="):
        return name, f"{low}, {high}{' + 1' if op == '<=' else ''}{stride}", is_nonnegative(scope, value)
    if not upward and op in (">", ">="):
        return name, f"{low}, {high}{' - 1' if op == '>=' else ''}{stride}", is_nonnegative(scope, bound)
    return None


def call_statement(scope: Scope, node: Node) -> list[str]:
    function = text(scope, child(scope, node, "function"))
    arguments = arguments_of(scope, node)
    if function in DROPPED:
        return []
    if function == "memset":
        if len(arguments) != 3 or expression(scope, arguments[1]) not in ("0", "0.0"):
            raise refuse(scope, node, "a memset to a value other than zero")
        return [f"{whole_array(scope, node, arguments[0], counted(scope, node, arguments[2]))} = 0"]
    if function == "memcpy" and len(arguments) == 3:
        count = counted(scope, node, arguments[2])
        target, source = (whole_array(scope, node, a, count) for a in arguments[:2])
        if target.count(",") != source.count(","):
            raise refuse(scope, node, "a memcpy between arrays of different rank")
        return [f"{target} = {source}"]
    if function in ("cblas_dgemm", "cblas_sgemm"):
        return [gemm(scope, node, arguments)]
    if function in ("cblas_dgemv", "cblas_sgemv"):
        return [gemv(scope, node, arguments)]
    if function in scope.functions:
        raise refuse(scope, node, "a call to a helper function of the file (inline it into the kernel)")
    raise refuse(scope, node, "a call to a function outside math.h and BLAS")


def counted(scope: Scope, node: Node, size: Node) -> sympy.Expr:
    """The element count of a byte size ``count * sizeof(T)``."""
    if not any(n.type == "sizeof_expression" for n in walk(size)):
        raise refuse(scope, node, "a byte count without sizeof")
    return sympy.Mul(*(extent(f) for f in factors(scope, size)))


def whole_array(scope: Scope, node: Node, argument: Node, count: sympy.Expr) -> str:
    """The array ``argument`` names, as a target over all of it (``A[:, :]``) or its first ``count`` elements."""
    inner = unwrap_cast(argument)
    if inner is None or inner.type != "identifier" or text(scope, inner) not in scope.arrays:
        raise refuse(scope, node, "a memory call on something other than a whole array")
    array = scope.arrays[text(scope, inner)]
    name = python_name(scope, text(scope, inner))
    if sympy.simplify(sympy.Mul(*(extent(s) for s in array.shape)) - count) == 0:
        return f"{name}[{', '.join(':' * len(array.shape))}]"
    if len(array.shape) == 1:
        return f"{name}[0:{printed(scope, count)}]"
    raise refuse(scope, node, "a memory call over part of a multidimensional array")


def operand(scope: Scope, node: Node, rows: str, cols: str, lead: Node, transposed: bool) -> str:
    """A BLAS operand as a matrix: the array (its leading rows, or reshaped from flat) and transposed."""
    inner = unwrap_cast(node)
    name = text(scope, inner) if inner is not None else ""
    if name not in scope.arrays:
        raise refuse(scope, node, "a BLAS operand that is no whole array (pointer arithmetic)")
    array = scope.arrays[name]
    target = python_name(scope, name)
    held = (cols, rows) if transposed else (rows, cols)
    if sympy.simplify(extent(expression(scope, lead)) - extent(held[1])) != 0:
        raise refuse(scope, node, "a BLAS call with a leading dimension other than the row length")
    shape = [extent(s) for s in array.shape]
    want = [extent(s) for s in held]
    if len(shape) == 2 and all(sympy.simplify(a - b) == 0 for a, b in zip(shape, want, strict=True)):
        spelled = target
    elif len(shape) == 2 and sympy.simplify(shape[1] - want[1]) == 0:
        spelled = f"{target}[0:{held[0]}, :]"
    elif len(shape) == 1:
        spelled = f"{target}.reshape(({held[0]}, {held[1]}))"
    else:
        raise refuse(scope, node, "a BLAS operand whose shape is not the matrix it passes")
    return f"{spelled}.T" if transposed else spelled


def vector(scope: Scope, node: Node, length: str, stride: Node) -> str:
    inner = unwrap_cast(node)
    name = text(scope, inner) if inner is not None else ""
    if name not in scope.arrays or len(scope.arrays[name].shape) != 1:
        raise refuse(scope, node, "a BLAS vector that is no one-dimensional array")
    if expression(scope, stride) != "1":
        raise refuse(scope, node, "a strided BLAS vector")
    target = python_name(scope, name)
    if sympy.simplify(extent(scope.arrays[name].shape[0]) - extent(length)) == 0:
        return target
    return f"{target}[0:{length}]"


def scaled(value: str, product: str) -> str:
    return product if value in ("1.0", "1") else f"{value} * ({product})"


def blas_store(target: str, rank: int, alpha: str, product: str, beta: str) -> str:
    """``target = alpha * product + beta * target`` over the whole target."""
    whole_target = target if target.endswith("]") else f"{target}[{', '.join(':' * rank)}]"
    if beta in ("0.0", "0"):
        return f"{whole_target} = {scaled(alpha, product)}"
    return f"{whole_target} = {scaled(alpha, product)} + {scaled(beta, target)}"


def gemm(scope: Scope, node: Node, arguments: list[Node]) -> str:
    """``cblas_dgemm(CblasRowMajor, ta, tb, M, N, K, alpha, A, lda, B, ldb, beta, C, ldc)`` as ``@``."""
    if len(arguments) != 14 or text(scope, arguments[0]) != "CblasRowMajor":
        raise refuse(scope, node, "a BLAS call outside row-major canonical form")
    m, n, k = (expression(scope, a) for a in arguments[3:6])
    a = operand(scope, arguments[7], m, k, arguments[8], text(scope, arguments[1]) == "CblasTrans")
    b = operand(scope, arguments[9], k, n, arguments[10], text(scope, arguments[2]) == "CblasTrans")
    c = operand(scope, arguments[12], m, n, arguments[13], False)
    alpha, beta = expression(scope, arguments[6]), expression(scope, arguments[11])
    return blas_store(c, 2, alpha, f"{a} @ {b}", beta)


def gemv(scope: Scope, node: Node, arguments: list[Node]) -> str:
    """``cblas_dgemv(CblasRowMajor, t, M, N, alpha, A, lda, x, incx, beta, y, incy)`` as ``@``."""
    if len(arguments) != 12 or text(scope, arguments[0]) != "CblasRowMajor":
        raise refuse(scope, node, "a BLAS call outside row-major canonical form")
    m, n = (expression(scope, a) for a in arguments[2:4])
    transposed = text(scope, arguments[1]) == "CblasTrans"
    a = operand(scope, arguments[5], m, n, arguments[6], False)
    x = vector(scope, arguments[7], m if transposed else n, arguments[8])
    y = vector(scope, arguments[10], n if transposed else m, arguments[11])
    alpha, beta = expression(scope, arguments[4]), expression(scope, arguments[9])
    return blas_store(y, 1, alpha, f"{a}.T @ {x}" if transposed else f"{a} @ {x}", beta)


def dot(scope: Scope, node: Node, arguments: list[Node]) -> str:
    """``cblas_ddot(n, x, incx, y, incy)`` as ``np.dot``."""
    if len(arguments) != 5:
        raise refuse(scope, node, "a BLAS call outside row-major canonical form")
    n = expression(scope, arguments[0])
    return f"np.dot({vector(scope, arguments[1], n, arguments[2])}, {vector(scope, arguments[3], n, arguments[4])})"


# ---------------------------------------------------------------------------------------------------- the kernel


def declarator_of(node: Node) -> Node | None:
    """The function declarator of a function definition."""
    found = node.child_by_field_name("declarator")
    while found is not None and found.type != "function_declarator":
        found = found.child_by_field_name("declarator")
    return found


def parameter_name(node: Node) -> Node | None:
    inner = node.child_by_field_name("declarator")
    while inner is not None and inner.type != "identifier":
        inner = inner.child_by_field_name("declarator")
    return inner


def read_file(scope: Scope) -> None:
    """The file's functions and its file-scope constants (``constexpr``, ``static const``, ``#define N 64``)."""
    from tree_sitter_language_pack import get_parser  # the grammar loads on first use

    for node in get_parser("c").parse(scope.source).root_node.named_children:
        if node.type == "function_definition":
            declarator = declarator_of(node)
            name = None if declarator is None else declarator.child_by_field_name("declarator")
            if name is not None:
                scope.functions[text(scope, name)] = node
        elif node.type == "declaration":
            file_constant(scope, node)
        elif node.type == "preproc_def":
            define(scope, node)


def file_constant(scope: Scope, node: Node) -> None:
    """A file-scope ``const``/``constexpr`` scalar with a literal value, as a module constant."""
    qualifiers = {text(scope, q) for q in node.named_children if q.type == "type_qualifier"}
    kind = node.child_by_field_name("type")
    if not qualifiers & {"const", "constexpr"} or kind is None or type_name(scope, kind) not in DTYPES:
        return
    dtype = DTYPES[type_name(scope, kind)]
    for declarator in node.children_by_field_name("declarator"):
        value, name = declarator.child_by_field_name("value"), declarator.child_by_field_name("declarator")
        if value is None or name is None or name.type != "identifier":
            continue
        try:
            literal = ast.literal_eval(expression(scope, value))
        except (Refused, ValueError, SyntaxError):
            continue
        if isinstance(literal, int | float) and not isinstance(literal, bool):
            scope.constants[text(scope, name)] = (repr(int(literal) if is_integer_dtype(dtype) else literal), dtype)


def define(scope: Scope, node: Node) -> None:
    """``#define N 64`` (a number literal, optionally parenthesized and negative) as a module constant."""
    name, value = node.child_by_field_name("name"), node.child_by_field_name("value")
    if name is None or value is None or text(scope, name) in CONSTANTS:
        return
    found = re.fullmatch(r"\(?\s*(-?\s*\d+\.?\d*(?:[eE][-+]?\d+)?)([uUlLfF]*)\s*\)?", text(scope, value).strip())
    if found is None:
        return
    digits, suffix = found.group(1).replace(" ", ""), found.group(2).lower()
    floating = any(c in digits.lower() for c in ".e") or "f" in suffix
    scope.constants[text(scope, name)] = (digits, "float64" if floating else "int64")


def lift(source: str, binding: dict[str, Any]) -> Lifted:
    """The kernel of ``binding`` (``kernel``, ``args`` with ``name``, ``kind``, ``shape``) as loop-level Python."""
    scope = Scope(source.encode())
    read_file(scope)
    if binding["kernel"] not in scope.functions:
        raise Refused("no function of the binding's name", binding["kernel"])
    node = scope.functions[binding["kernel"]]
    declarator = declarator_of(node)
    assert declarator is not None
    for arg in binding["args"]:
        kind = arg["kind"]
        if kind.startswith("ptr_") and kind[4:] in KINDS:
            shape = tuple(str(s).replace("/", "//") for s in arg.get("shape") or ["1"])
            scope.arrays[arg["name"]] = Array(KINDS[kind[4:]], shape)
        elif kind in KINDS:
            scope.scalars[arg["name"]] = KINDS[kind]
        else:
            raise Refused("an argument of a type outside canonical C form", f"{arg['name']}: {kind}")
    parameters: list[str] = []
    for parameter in child(scope, declarator, "parameters").named_children:
        name_node = parameter_name(parameter)
        if name_node is None or not (text(scope, name_node) in scope.arrays or text(scope, name_node) in scope.scalars):
            raise refuse(scope, parameter, "a parameter the binding does not name")
        parameters.append(python_name(scope, text(scope, name_node)))
    # extents: the binding's integer scalars named in a shape, non-negative and respelled as Python names
    for array in scope.arrays.values():
        words = {w for s in array.shape for w in re.findall(r"[A-Za-z_]\w*", s)}
        scope.nonnegative |= {w for w in words if is_integer_dtype(scope.scalars.get(w, "float64"))}
        array.shape = tuple(respell(scope, s) for s in array.shape)
    body = statement(scope, child(scope, node, "body"))
    return Lifted(parameters, body, scope)


def respell(scope: Scope, value: str) -> str:
    """An extent over C names as one over the kernel's Python names."""

    def name(found: re.Match[str]) -> str:
        word = found.group(0)
        if word in scope.constants:
            scope.used.add(word)
            return python_identifier(word)
        return python_name(scope, word) if word in scope.scalars else word

    return re.sub(r"[A-Za-z_]\w*", name, value)


# ---------------------------------------------------------------------------------------------------- idioms


def canonical(value: str) -> str:
    """An extent in one spelling, so ``(N - 1)`` and ``N-1`` compare equal."""
    try:
        return str(extent(value)).replace(" ", "")
    except (SyntaxError, sympy.SympifyError, TypeError, AssertionError):
        return value


def shape_of(value: ast.expr) -> tuple[str, ...] | None:
    """The shape of ``np.empty((A, B), dtype=...)`` or ``np.zeros``, as canonical extents."""
    if not (isinstance(value, ast.Call) and ast.unparse(value.func) in ("np.empty", "np.zeros") and value.args):
        return None
    shape = value.args[0]
    return tuple(canonical(ast.unparse(i)) for i in (shape.elts if isinstance(shape, ast.Tuple) else [shape]))


def range_of(loop: ast.For) -> tuple[str, str] | None:
    """(variable, extent) of ``for v in range(0, extent)``."""
    if not isinstance(loop.target, ast.Name) or not isinstance(loop.iter, ast.Call) or loop.orelse:
        return None
    args = loop.iter.args
    if ast.unparse(loop.iter.func) != "range" or len(args) != 2 or ast.unparse(args[0]) != "0":
        return None
    return loop.target.id, canonical(ast.unparse(args[1]))


def nest(loop: ast.For) -> tuple[list[tuple[str, str]], list[ast.stmt]]:
    """The perfectly nested full ranges from ``loop`` down, and the innermost body."""
    ranges: list[tuple[str, str]] = []
    body: list[ast.stmt] = [loop]
    while len(body) == 1 and isinstance(body[0], ast.For) and (found := range_of(body[0])) is not None:
        ranges.append(found)
        body = body[0].body
    return ranges, body


def index_names(node: ast.Subscript) -> tuple[str, ...] | None:
    items = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
    names = tuple(i.id for i in items if isinstance(i, ast.Name))
    return names if len(names) == len(items) else None


def names_in(node: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def call_np(name: str, *args: ast.expr) -> ast.Call:
    return ast.Call(ast.Attribute(ast.Name("np", ast.Load()), name, ast.Load()), list(args), [])


def whole(name: str, rank: int) -> ast.Subscript:
    """``name[:, :]`` over ``rank`` axes."""
    slices: list[ast.expr] = [ast.Slice() for _ in range(rank)]
    return ast.Subscript(ast.Name(name, ast.Load()), slices[0] if rank == 1 else ast.Tuple(slices, ast.Load()))


class Vectorize(ast.NodeTransformer):
    """``X[v...]`` (``X`` of the nest's shape) as ``X``; anything else naming a loop variable or an array fails."""

    def __init__(self, shapes: dict[str, tuple[str, ...]], variables: tuple[str, ...], extents: tuple[str, ...]):
        self.shapes = shapes
        self.variables = variables
        self.extents = extents
        self.failed = False
        self.arrays = 0

    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        if isinstance(node.value, ast.Name) and index_names(node) == self.variables:
            if self.shapes.get(node.value.id) == self.extents:
                self.arrays += 1
                return ast.Name(node.value.id, ast.Load())
        self.failed = True
        return node

    def visit_Name(self, node: ast.Name) -> ast.AST:
        self.failed |= node.id in self.variables or node.id in self.shapes
        return node

    def visit_IfExp(self, node: ast.IfExp) -> ast.AST:
        self.generic_visit(node)
        return call_np("where", node.test, node.body, node.orelse)

    def visit_BoolOp(self, node: ast.BoolOp) -> ast.AST:
        self.generic_visit(node)
        out = node.values[0]
        for value in node.values[1:]:
            out = call_np("logical_and" if isinstance(node.op, ast.And) else "logical_or", out, value)
        return out

    def visit_UnaryOp(self, node: ast.UnaryOp) -> ast.AST:
        self.generic_visit(node)
        return call_np("logical_not", node.operand) if isinstance(node.op, ast.Not) else node

    def visit_Call(self, node: ast.Call) -> ast.AST:
        self.generic_visit(node)
        self.failed |= not ast.unparse(node.func).startswith("np.")  # c_div and c_mod work on scalars
        return node


def vectorized(
    shapes: dict[str, tuple[str, ...]], expr: ast.expr, variables: tuple[str, ...], extents: tuple[str, ...]
) -> tuple[ast.expr, int] | None:
    """``expr`` over the whole nest and how many arrays it reads, or None."""
    rewrite = Vectorize(shapes, variables, extents)
    out = rewrite.visit(ast.parse(ast.unparse(expr), mode="eval").body)
    return None if rewrite.failed or not isinstance(out, ast.expr) else (out, rewrite.arrays)


def array_target(shapes: dict[str, tuple[str, ...]], target: ast.expr, ranges: list[tuple[str, str]]) -> str | None:
    """The array ``target`` writes when it is ``X[v...]`` over the nest's variables and ``X`` has its extents."""
    if not isinstance(target, ast.Subscript) or not isinstance(target.value, ast.Name):
        return None
    name = target.value.id
    if index_names(target) != tuple(v for v, _ in ranges) or shapes.get(name) != tuple(e for _, e in ranges):
        return None
    return name


def elementwise(shapes: dict[str, tuple[str, ...]], loop: ast.For) -> ast.stmt | None:
    """A full-range nest whose one statement writes ``X[v...]`` and reads arrays only at ``[v...]``, as one
    whole-array statement."""
    ranges, body = nest(loop)
    if not ranges or len(body) != 1 or not isinstance(body[0], ast.Assign | ast.AugAssign):
        return None
    stmt = body[0]
    target = stmt.target if isinstance(stmt, ast.AugAssign) else stmt.targets[0]
    name = array_target(shapes, target, ranges)
    found = None if name is None else vectorized(shapes, stmt.value, *map(tuple, zip(*ranges, strict=True)))
    if name is None or found is None:
        return None
    if isinstance(stmt, ast.AugAssign):
        return ast.AugAssign(whole(name, len(ranges)), stmt.op, found[0])
    return ast.Assign([whole(name, len(ranges))], found[0])


def reduction(shapes: dict[str, tuple[str, ...]], loop: ast.For) -> list[ast.stmt] | None:
    """``for o...: [T[o] = c;] for r...: T[o] += e[o..., r...]`` as ``T[:] = c + np.sum(e, axis=...)``; without
    outer loops, ``s += e[r...]`` into a scalar as ``s += np.sum(e)``."""
    outer, body = nest(loop)
    init: ast.Assign | None = None
    if len(body) == 2 and isinstance(body[0], ast.Assign) and isinstance(body[1], ast.For):
        init, body = body[0], body[1:]
    if outer and len(body) == 1 and isinstance(body[0], ast.For):
        inner, body = nest(body[0])
    elif init is None:
        outer, inner = [], outer
    else:
        return None
    if not inner or len(body) != 1 or not isinstance(body[0], ast.AugAssign) or not isinstance(body[0].op, ast.Add):
        return None
    update = body[0]
    if outer:
        name = array_target(shapes, update.target, outer)
        if name is None:
            return None
    elif isinstance(update.target, ast.Name):
        name = update.target.id
    else:
        return None
    if name in names_in(update.value):
        return None
    every = outer + inner
    if init is not None and not (
        len(init.targets) == 1
        and ast.dump(init.targets[0]) == ast.dump(update.target)
        and not names_in(init.value) & ({v for v, _ in every} | shapes.keys())
    ):
        return None
    found = vectorized(shapes, update.value, *map(tuple, zip(*every, strict=True)))
    if found is None or found[1] == 0:
        return None
    total = call_np("sum", found[0])
    if not outer:
        return [ast.AugAssign(ast.Name(name, ast.Store()), ast.Add(), total)]
    axes = [ast.Constant(a) for a in range(len(outer), len(every))]
    total.keywords = [ast.keyword("axis", axes[0] if len(axes) == 1 else ast.Tuple(list(axes), ast.Load()))]
    out = whole(name, len(outer))
    if init is None:
        return [ast.AugAssign(out, ast.Add(), total)]
    if isinstance(init.value, ast.Constant) and init.value.value == 0:
        return [ast.Assign([out], total)]
    return [ast.Assign([out], ast.BinOp(init.value, ast.Add(), total))]


def matmul(shapes: dict[str, tuple[str, ...]], loop: ast.For) -> list[ast.stmt] | None:
    """``for i: for j: X[i, j] = 0; for l: X[i, j] += Y[i, l] * Z[l, j]`` as ``X[:, :] = Y @ Z`` (transposes too);
    without the zero, as ``X[:, :] += Y @ Z``."""
    outer, body = nest(loop)
    if len(outer) != 2:
        return None
    (i, m), (j, n) = outer
    init: ast.Assign | None = None
    if len(body) == 2 and isinstance(body[0], ast.Assign):
        init, body = body[0], body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.For):
        return None
    inner = range_of(body[0])
    if inner is None or len(body[0].body) != 1 or not isinstance(body[0].body[0], ast.AugAssign):
        return None
    (variable, k), update = inner, body[0].body[0]
    name = array_target(shapes, update.target, outer)
    product = update.value
    if name is None or not isinstance(update.op, ast.Add):
        return None
    if not (isinstance(product, ast.BinOp) and isinstance(product.op, ast.Mult)):
        return None
    if init is not None and not (
        len(init.targets) == 1
        and ast.dump(init.targets[0]) == ast.dump(update.target)
        and isinstance(init.value, ast.Constant)
        and init.value.value == 0
    ):
        return None
    spelled: list[str] = []
    for side, rows, cols, want in ((product.left, m, k, (i, variable)), (product.right, k, n, (variable, j))):
        if not isinstance(side, ast.Subscript) or not isinstance(side.value, ast.Name) or side.value.id == name:
            return None
        names, shape = index_names(side), shapes.get(side.value.id)
        if names == want and shape == (rows, cols):
            spelled.append(side.value.id)
        elif names == want[::-1] and shape == (cols, rows):
            spelled.append(f"{side.value.id}.T")
        else:
            return None
    value = ast.parse(f"{spelled[0]} @ {spelled[1]}", mode="eval").body
    if init is not None:
        return [ast.Assign([whole(name, 2)], value)]
    return [ast.AugAssign(whole(name, 2), ast.Add(), value)]


class Raise(ast.NodeTransformer):
    """Every loop nest that matches an idiom, innermost first; array shapes follow the statements in order."""

    def __init__(self, shapes: dict[str, tuple[str, ...]]) -> None:
        self.shapes = shapes

    def visit_Assign(self, node: ast.Assign) -> ast.AST:
        target, value = node.targets[0], node.value
        if isinstance(target, ast.Name):
            shape = shape_of(value)
            if shape is None and isinstance(value, ast.Name):
                shape = self.shapes.get(value.id)
            if shape is None:
                self.shapes.pop(target.id, None)
            else:
                self.shapes[target.id] = shape
        if (
            isinstance(value, ast.BinOp)
            and isinstance(target, ast.Name | ast.Subscript)
            and isinstance(value.op, ast.Add | ast.Sub | ast.Mult)
            and ast.unparse(value.left) == ast.unparse(target)
        ):
            return ast.AugAssign(target, value.op, value.right)  # x = x + e as x += e
        return node

    def visit_For(self, node: ast.For) -> ast.AST | list[ast.stmt]:
        self.generic_visit(node)
        found = matmul(self.shapes, node) or reduction(self.shapes, node)
        if found is not None:
            return found
        return elementwise(self.shapes, node) or node


def raise_idioms(lifted: Lifted) -> list[ast.stmt]:
    """The lifted body with its loop nests raised to NumPy statements."""
    scope = lifted.scope
    shapes = {
        scope.renamed[c]: tuple(canonical(s) for s in a.shape)
        for c, a in scope.arrays.items()
        if c in scope.renamed and scope.renamed[c] in lifted.parameters
    }
    tree = Raise(shapes).visit(ast.parse("\n".join(lifted.body) or "pass"))
    return ast.fix_missing_locations(tree).body


# ---------------------------------------------------------------------------------------------------- module

HELPERS = '''def c_div(a, b):
    """C's integer division: the quotient truncated toward zero."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def c_mod(a, b):
    """C's integer remainder: the sign of the dividend."""
    return a - b * c_div(a, b)'''


def emit(lifted: Lifted, body: list[ast.stmt], name: str = "kernel", typed: bool = False) -> str:
    """The NumPy module; ``typed`` makes it a ``@dace.program`` whose parameters carry DaCe types and whose
    extents are DaCe symbols."""
    scope = lifted.scope
    original = {p: c for c, p in scope.renamed.items()}
    header = ["import numpy as np"]
    signature = ", ".join(lifted.parameters)
    if typed:
        words = {w for a in scope.arrays.values() for s in a.shape for w in re.findall(r"[A-Za-z_]\w*", s)}
        symbols = sorted(p for p in lifted.parameters if p in words)
        header = ["import dace", *header, *(f"{s} = dace.symbol('{s}', dace.int64)" for s in symbols)]
        signature = ", ".join(f"{p}: {annotation(scope, original[p])}" for p in lifted.parameters if p not in symbols)
    constants = [f"{python_identifier(c)} = {scope.constants[c][0]}" for c in sorted(scope.used)]
    function = ast.parse(f"def {name}({signature}):\n    pass").body[0]
    assert isinstance(function, ast.FunctionDef)
    function.body = body or [ast.Pass()]
    if typed:
        function.decorator_list = [ast.parse("dace.program", mode="eval").body]
    source = ast.unparse(ast.fix_missing_locations(ast.Module([function], [])))
    parts = ["\n".join(header + constants)]
    if "c_div(" in source or "c_mod(" in source:
        parts.append(HELPERS)
    return "\n\n\n".join([*parts, source]) + "\n"


def annotation(scope: Scope, name: str) -> str:
    """The DaCe type of the kernel's parameter ``name`` (C spelling)."""
    if name in scope.arrays:
        array = scope.arrays[name]
        return f"dace.{array.dtype}[{', '.join(array.shape)}]"
    return f"dace.{scope.scalars[name]}"


def translate(source: str, binding: dict[str, Any], name: str = "kernel") -> str:
    """The NumPy module of the C kernel ``binding["kernel"]`` in ``source``; raises :class:`Refused` outside
    canonical C form."""
    lifted = lift(source, binding)
    return emit(lifted, raise_idioms(lifted), name)


def to_sdfg(source: str, binding: dict[str, Any], folder: pathlib.Path | None = None) -> "dace.SDFG":
    """The SDFG of the C kernel: its NumPy module as a ``@dace.program`` parsed by DaCe. The module is written to
    ``folder`` (a temporary one without it): DaCe reads a program's source from its file."""
    lifted = lift(source, binding)
    where = folder or pathlib.Path(tempfile.mkdtemp(prefix="cnumpy_"))
    where.mkdir(parents=True, exist_ok=True)
    path = where / f"{binding['kernel']}_numpy.py"
    path.write_text(emit(lifted, raise_idioms(lifted), binding["kernel"], typed=True))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # DaCe resolves the program's globals through its module
    spec.loader.exec_module(module)
    return module.__dict__[binding["kernel"]].to_sdfg()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m alloy.frontend.cnumpy", description=__doc__)
    parser.add_argument("source", type=pathlib.Path, help="the C file")
    parser.add_argument("binding", type=pathlib.Path, help="the bench's <kernel>_binding.json")
    parser.add_argument("--out", type=pathlib.Path, help="write the NumPy module here instead of to stdout")
    parser.add_argument("--sdfg", type=pathlib.Path, help="also write the kernel's SDFG here (DaCe parses the NumPy)")
    args = parser.parse_args(argv)
    source, binding = args.source.read_text(), json.loads(args.binding.read_text())
    try:
        module = translate(source, binding)
        if args.sdfg is not None:
            to_sdfg(source, binding, args.sdfg.parent).save(str(args.sdfg))
    except Refused as why:
        print(f"refused: {why}", file=sys.stderr)
        return 1
    if args.out is None:
        print(module, end="")
    else:
        args.out.write_text(module)
    return 0


if __name__ == "__main__":
    sys.exit(main())
