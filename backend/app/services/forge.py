"""The ForgeEngine: source -> agent-native CLI command manifest.

Pure, deterministic, offline. Combines entry-point extraction with a shell
command renderer to produce a manifest that an agent can execute directly.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.parser import (
    ArgumentSpec,
    EntryPoint,
    SUPPORTED_LANGUAGES,
    extract_entry_points,
)


@dataclass
class ForgedArgument:
    name: str
    py_type: str
    cli_type: str
    required: bool
    default: str | None
    help: str


@dataclass
class ForgedCommand:
    name: str
    kind: str
    docstring: str
    location: str
    arguments: list[ForgedArgument] = field(default_factory=list)
    rendered: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ForgeResult:
    program_name: str
    language: str
    commands: list[ForgedCommand] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "program_name": self.program_name,
            "language": self.language,
            "commands": [c.to_dict() for c in self.commands],
            "error": self.error,
        }


def render_command(program_name: str, cmd: ForgedCommand) -> str:
    """Render an executable shell command template for one entry point.

    * required positional -> ``<NAME>``
    * boolean flag default false -> ``[--name]``
    * boolean flag default true  -> ``[--name/--no-name]``
    * optional scalar          -> ``[--name <VALUE>]``
    """
    parts = [program_name, cmd.name]
    for arg in cmd.arguments:
        if arg.cli_type == "boolean":
            if arg.default == "True":
                parts.append("[--%s/--no-%s]" % (arg.name, arg.name))
            else:
                parts.append("[--%s]" % arg.name)
        elif arg.required:
            parts.append("<%s>" % arg.name.upper())
        else:
            parts.append("[--%s <VALUE>]" % arg.name)
    return " ".join(parts)


def _map_arg(arg: ArgumentSpec) -> ForgedArgument:
    return ForgedArgument(
        name=arg.name,
        py_type=arg.py_type,
        cli_type=arg.cli_type,
        required=arg.required,
        default=arg.default_repr,
        help=arg.help,
    )


class ForgeEngine:
    """Forge agent-native CLI manifests from source code (offline)."""

    def forge(self, source: str, program_name: str, language: str = "python") -> ForgeResult:
        if language.lower() not in SUPPORTED_LANGUAGES:
            return ForgeResult(program_name=program_name, language=language,
                               commands=[], error="unsupported language: %s" % language)
        try:
            points: list[EntryPoint] = extract_entry_points(source)
        except ValueError as exc:  # syntax error, surfaced by parser
            return ForgeResult(program_name=program_name, language=language,
                               commands=[], error=str(exc))

        commands: list[ForgedCommand] = []
        for pt in points:
            cmd = ForgedCommand(
                name=pt.name,
                kind=pt.kind,
                docstring=pt.docstring,
                location=pt.location,
                arguments=[_map_arg(a) for a in pt.arguments],
            )
            cmd.rendered = render_command(program_name, cmd)
            commands.append(cmd)
        return ForgeResult(program_name=program_name, language=language,
                           commands=commands, error=None)


__all__ = ["ForgeEngine", "ForgeResult", "ForgedCommand", "ForgedArgument", "render_command"]