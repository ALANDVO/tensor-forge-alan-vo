"""Deterministic AST extraction of CLI entry points from Python source.

This is the offline core of tensor-forge. It inspects Python source code
structure only (no LLM, no network) and recovers candidate CLI entry points:

* top-level function definitions -> one CLI command per function,
* ``argparse`` call sites (``ArgumentParser`` + ``.parse_args()``) -> a
  synthesized ``main`` command whose arguments are recovered from
  ``.add_argument(...)`` calls,
* an ``if __name__ == "__main__":`` block -> a ``main`` entry point.

Each argument carries a name, Python type (from annotations), a CLI type,
whether it is required, its default, and a one-line help string taken from
the function docstring when available.
"""
from __future__ import annotations

import ast
import textwrap
from dataclasses import dataclass, field

# Languages this engine can parse deterministically. More are planned.
SUPPORTED_LANGUAGES = ("python",)

#: Maps Python annotation names to a descriptive CLI type label.
TYPE_TO_CLI = {
    "int": "integer",
    "str": "string",
    "bool": "boolean",
    "float": "number",
    "list": "array",
    "dict": "object",
}


def _name(attr: str, fallback: str = "Any") -> str:
    return attr or fallback


@dataclass
class ArgumentSpec:
    name: str
    py_type: str
    cli_type: str
    required: bool
    default_repr: str | None
    help: str


@dataclass
class EntryPoint:
    name: str
    kind: str  # "function" | "argparse" | "main_block"
    arguments: list[ArgumentSpec] = field(default_factory=list)
    docstring: str = ""
    location: str = ""


# --------------------------------------------------------------------------- #
# Annotation helpers
# --------------------------------------------------------------------------- #
def _annotation_name(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return _name(str(node.value))
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _annotation_name(node.value)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        # PEP 604 union like str | None
        return "|".join(
            filter(None, (_annotation_name(node.left), _annotation_name(node.right)))
        )
    return None


def _cli_type_for(annotation_name: str | None) -> str:
    if not annotation_name:
        return "string"
    return TYPE_TO_CLI.get(annotation_name.split("|")[0], "string")


def _strip_optional(name: str | None) -> str:
    """``str | None`` -> ``str``; ``Optional[str]`` handled by caller."""
    if not name:
        return "Any"
    return name.split("|")[0].strip()


# --------------------------------------------------------------------------- #
# Default value rendering
# --------------------------------------------------------------------------- #
def _is_bool_constant(node: ast.expr | None) -> bool | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.Constant) and node.value is None:
        return None
    return None


def _default_repr(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.NameConstant):  # py<3.8 compat (not reached on 3.12)
        return repr(node.value)
    if isinstance(node, ast.Name):
        return node.id
    return "<expr>"


# --------------------------------------------------------------------------- #
# Docstring summary extraction
# --------------------------------------------------------------------------- #
def _docstring_summary(node: ast.AST) -> str:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
        doc = ast.get_docstring(node, clean=False)
    else:
        doc = None
    if not doc:
        return ""
    first = textwrap.dedent(doc).strip().splitlines()
    return first[0].strip() if first else ""


# --------------------------------------------------------------------------- #
# Signature argument extraction
# --------------------------------------------------------------------------- #
def _build_args(posonly: list[ast.arg], args: list[ast.arg], defaults: list[ast.expr],
                kwonly: list[ast.arg], kw_defaults: list[ast.expr | None]) -> list[ArgumentSpec]:
    """Recover named parameters and their default status.

    Defaults align to the *tail* of the positional parameters. Keyword-only
    parameters pair 1:1 with ``kw_defaults`` (a ``None`` default means the
    parameter is required).
    """
    specs: list[ArgumentSpec] = []

    def _spec(arg: ast.arg, has_default: bool, default_node: ast.expr | None) -> ArgumentSpec:
        ann = _annotation_name(arg.annotation)
        py_type = _strip_optional(ann)
        is_bool = _is_bool_constant(default_node)
        if is_bool is False or is_bool is True:
            # boolean flag: required only if no default (impossible here) -> optional
            return ArgumentSpec(
                name=arg.arg,
                py_type=py_type,
                cli_type="boolean",
                required=False,
                default_repr=_default_repr(default_node),
                help="",
            )
        return ArgumentSpec(
            name=arg.arg,
            py_type=py_type,
            cli_type=_cli_type_for(ann),
            required=not has_default,
            default_repr=_default_repr(default_node),
            help="",
        )

    named = list(posonly) + list(args)
    first_default = len(named) - len(defaults)
    for i, arg in enumerate(named):
        has_default = i >= first_default
        default_node = defaults[i - first_default] if has_default else None
        specs.append(_spec(arg, has_default, default_node))

    for arg, default_node in zip(kwonly, kw_defaults):
        specs.append(_spec(arg, default_node is not None, default_node))

    return specs


# Argparse extraction
# --------------------------------------------------------------------------- #
@dataclass
class _ArgparseCall:
    flags: list[str]
    dest: str | None
    help: str | None
    py_type: str | None
    default_repr: str | None
    required: bool | None


def _argparse_add_argument(call: ast.Call) -> _ArgparseCall | None:
    """Best-effort recovery of a single ``add_argument`` call."""
    if not (isinstance(call.func, ast.Attribute) and call.func.attr == "add_argument"):
        return None
    flags: list[str] = []
    opts: dict[str, ast.expr] = {}
    for arg in call.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            flags.append(arg.value)
    for kw in call.keywords:
        opts[kw.arg] = kw.value
    dest = None
    if "dest" in opts and isinstance(opts["dest"], ast.Constant):
        dest = opts["dest"].value
        flags.append("--" + dest if not dest.startswith("-") else dest)
    if not dest and flags:
        # first --flag form
        for f in flags:
            if f.startswith("--"):
                dest = f.lstrip("-")
                break
    help_text = None
    if "help" in opts and isinstance(opts["help"], ast.Constant):
        help_text = str(opts["help"].value)
    action = opts.get("action")
    is_bool = False
    if isinstance(action, ast.Constant) and action.value == "store_true":
        is_bool = True
    py_type = "boolean" if is_bool else _annotation_name(opts.get("type"))
    default_node = opts.get("default")
    default_rep = _default_repr(default_node)
    required = None
    if "required" in opts and isinstance(opts["required"], ast.Constant):
        required = bool(opts["required"].value)
    return _ArgparseCall(
        flags=flags,
        dest=dest,
        help=help_text,
        py_type=py_type,
        default_repr=default_rep,
        required=required,
    )


def _argparse_entry_points(tree: ast.Module) -> list[EntryPoint]:
    """Synthesize one ``main`` entry point from argparse usage in the module."""
    add_calls: list[_ArgparseCall] = []
    has_parse_args = False
    has_main_block = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "parse_args":
                has_parse_args = True
            parsed = _argparse_add_argument(node)
            if parsed is not None:
                add_calls.append(parsed)
        if isinstance(node, ast.If):
            if _is_main_guard(node):
                has_main_block = True
    if not (has_parse_args or has_main_block):
        return []

    args: list[ArgumentSpec] = []
    for c in add_calls:
        # Resolve the destination name.
        if c.dest:
            dest = c.dest
        else:
            dest = next((f.lstrip("-") for f in c.flags if f.startswith("--")), None)
            if not dest and c.flags:
                dest = c.flags[0]  # positional argument
        if not dest:
            continue
        is_bool = c.py_type == "boolean"
        if is_bool:
            required = False
            cli_type = "boolean"
            py_type = "bool"
        elif c.required is not None:
            required = c.required
            py_type = _strip_optional(c.py_type) if c.py_type else "string"
            cli_type = _cli_type_for(c.py_type)
        else:
            is_optional = any(f.startswith("--") for f in c.flags)
            required = not is_optional
            py_type = _strip_optional(c.py_type) if c.py_type else "string"
            cli_type = _cli_type_for(c.py_type)
        args.append(ArgumentSpec(
            name=dest, py_type=py_type, cli_type=cli_type,
            required=required, default_repr=c.default_repr, help=c.help or "",
        ))
    kind = "argparse" if has_parse_args else "main_block"
    return [EntryPoint(name="main", kind=kind, arguments=args, docstring="argparse entry point", location="module")]


def _is_main_guard(node: ast.If) -> bool:
    test = node.test
    if isinstance(test, ast.Compare) and isinstance(test.left, ast.Name):
        if test.left.id == "__name__":
            for cmp in test.comparators:
                if isinstance(cmp, ast.Constant) and cmp.value == "__main__":
                    return True
    return False


# --------------------------------------------------------------------------- #
# Public entry point
# --------------------------------------------------------------------------- #
def extract_entry_points(source: str) -> list[EntryPoint]:
    """Parse Python source and return discovered CLI entry points.

    Raises ``ValueError`` with a safe, line-located message on syntax errors.
    """
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError as exc:  # surface a clean, non-leaky message
        lineno = f"line {exc.lineno}" if exc.lineno else "unknown"
        raise ValueError(f"Syntax error in source ({lineno}): {exc.msg}") from exc

    points: list[EntryPoint] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_") and node.name != "__main__":
                # private helpers are not CLI entry points
                continue
            spec_args = _build_args(node.args.posonlyargs, node.args.args,
                                    node.args.defaults, node.args.kwonlyargs,
                                    node.args.kw_defaults)
            # prefer the first line of the docstring as help for every arg
            summary = _docstring_summary(node)
            for s in spec_args:
                if not s.help and summary:
                    s.help = summary
            points.append(EntryPoint(
                name=node.name,
                kind="function",
                arguments=spec_args,
                docstring=summary,
                location=f"line {node.lineno}",
            ))
    points.extend(_argparse_entry_points(tree))
    return points


def supported_languages() -> tuple[str, ...]:
    return SUPPORTED_LANGUAGES


__all__ = [
    "ArgumentSpec",
    "EntryPoint",
    "SUPPORTED_LANGUAGES",
    "extract_entry_points",
    "supported_languages",
]
