"""Domain-engine tests for the ForgeEngine (deterministic, no network)."""
from __future__ import annotations

import json

from app.services.forge import ForgeEngine, ForgedArgument, ForgedCommand, render_command
from app.services.parser import ArgumentSpec

SIMPLE_SRC = '''
def greet(name: str, times: int = 1, verbose: bool = False) -> str:
    """Greet a person by name."""
    return f"hi {name}"

def _internal():
    """Skipped private helper."""
    return None
'''

ARGPARSE_SRC = '''
import argparse

def build_parser():
    """Build the CLI parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--name", default="x", help="your name")
    parser.add_argument("-v", "--verbose", action="store_true", help="be loud")
    parser.add_argument("target", help="target file")
    parser.parse_args()
'''

SYNTAX_SRC = "def broken(:\n"
BOOL_TRUE_SRC = 'def flag(active: bool = True):\n    """Toggle feature."""\n    return active\n'


def test_forge_function_with_signature():
    engine = ForgeEngine()
    result = engine.forge(SIMPLE_SRC, "myapp")
    assert result.error is None
    assert result.program_name == "myapp"
    assert result.language == "python"
    names = {c.name for c in result.commands}
    assert "greet" in names
    assert "_internal" not in names  # private skipped


def test_forge_required_positional_and_optionals():
    result = ForgeEngine().forge(SIMPLE_SRC, "myapp")
    greet = next(c for c in result.commands if c.name == "greet")
    by = {a.name: a for a in greet.arguments}
    assert by["name"].required is True
    assert by["times"].required is False
    assert by["times"].default == "1"
    assert by["times"].py_type == "int"
    assert by["verbose"].cli_type == "boolean"
    assert by["verbose"].default == "False"


def test_forge_bool_default_true_renders_toggle():
    result = ForgeEngine().forge(BOOL_TRUE_SRC, "app")
    cmd = result.commands[0]
    assert cmd.name == "flag"
    assert "[--active/--no-active]" in cmd.rendered


def test_forge_argparse_detected_as_entry_point():
    result = ForgeEngine().forge(ARGPARSE_SRC, "cli")
    kinds = {c.kind for c in result.commands}
    assert "argparse" in kinds
    main = next(c for c in result.commands if c.name == "main" and c.kind == "argparse")
    arg_names = {a.name for a in main.arguments}
    assert "name" in arg_names
    assert "target" in arg_names  # positional add_argument
    assert "verbose" in arg_names


def test_forge_unsupported_language_returns_error():
    result = ForgeEngine().forge("print(1)", "app", language="rust")
    assert result.error is not None
    assert "unsupported language" in result.error
    assert result.commands == []


def test_forge_syntax_error_returns_error_not_exception():
    result = ForgeEngine().forge(SYNTAX_SRC, "app")
    assert result.error is not None
    assert "Syntax error" in result.error


def test_forge_private_functions_are_skipped():
    result = ForgeEngine().forge(SIMPLE_SRC, "app")
    names = {c.name for c in result.commands}
    assert "_internal" not in names


def test_forge_empty_module_has_no_commands():
    # a single newline is syntactically valid (empty module): no entry points
    result = ForgeEngine().forge("\n", "app")
    assert result.error is None
    assert result.commands == []


def test_render_command_required_positional():
    arg = ForgedArgument(name="user", py_type="str", cli_type="string", required=True,
                         default=None, help="")
    cmd = ForgedCommand(name="cmd", kind="function", docstring="", location="",
                        arguments=[arg])
    rendered = render_command("prog", cmd)
    assert "<USER>" in rendered
    assert rendered.startswith("prog cmd")


def test_render_command_optional_flag():
    arg = ForgedArgument(name="verbose", py_type="bool", cli_type="boolean",
                         required=False, default="False", help="")
    cmd = ForgedCommand(name="cmd", kind="function", docstring="", location="",
                        arguments=[arg])
    assert "[--verbose]" in render_command("prog", cmd)


def test_forge_docstring_used_as_help():
    result = ForgeEngine().forge(SIMPLE_SRC, "app")
    greet = next(c for c in result.commands if c.name == "greet")
    assert greet.arguments[0].help == "Greet a person by name."


def test_forge_keeps_location_line_numbers():
    result = ForgeEngine().forge(SIMPLE_SRC, "app")
    greet = next(c for c in result.commands if c.name == "greet")
    assert greet.location.startswith("line ")


def test_forge_optional_with_default_renders_bracketed_value():
    result = ForgeEngine().forge(SIMPLE_SRC, "app")
    greet = next(c for c in result.commands if c.name == "greet")
    times = next(a for a in greet.arguments if a.name == "times")
    assert times.required is False
    assert "[--times <VALUE>]" in greet.rendered


def test_forge_result_to_dict_serializable():
    result = ForgeEngine().forge(SIMPLE_SRC, "app")
    d = result.to_dict()
    assert d["program_name"] == "app"
    assert isinstance(d["commands"], list)
    assert d["commands"][0]["rendered"]
    json.dumps(d)  # must be JSON-serializable


def test_argument_spec_dataclass_roundtrip():
    spec = ArgumentSpec(name="n", py_type="int", cli_type="integer", required=False,
                        default_repr="3", help="count")
    assert spec.name == "n"
    assert spec.default_repr == "3"