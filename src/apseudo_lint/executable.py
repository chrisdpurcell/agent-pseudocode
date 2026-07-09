"""Executable Agent Pseudocode script parsing.

This module handles the small metadata envelope used by ``apseudo-run``. The
pseudocode body remains the same Pythonic Agent Pseudocode dialect used by the
validator and formatter; the shebang and frontmatter are only runner metadata.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, TypeAlias, cast

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
AgentName: TypeAlias = Literal["claude", "codex"]
RunMode: TypeAlias = Literal["plan", "review", "apply", "danger"]
WorkspaceMode: TypeAlias = Literal["cwd", "script_dir", "git_root"]

VALID_AGENTS: frozenset[str] = frozenset({"claude", "codex"})
VALID_MODES: frozenset[str] = frozenset({"plan", "review", "apply", "danger"})
VALID_WORKSPACES: frozenset[str] = frozenset({"cwd", "script_dir", "git_root"})


def _empty_json_dict() -> dict[str, JsonValue]:
    return {}


@dataclass(frozen=True, slots=True)
class ExecutableScript:
    """Parsed executable ``.apseudo`` script."""

    path: Path
    shebang: str | None
    frontmatter: str | None
    body: str
    body_start_line: int
    metadata: ScriptMetadata


@dataclass(frozen=True, slots=True)
class ScriptMetadata:
    """Runner metadata parsed from frontmatter."""

    name: str | None = None
    description: str | None = None
    default_agent: AgentName | None = None
    mode: RunMode = "plan"
    workspace: WorkspaceMode | str = "git_root"
    requires_clean_git: bool = False
    allow_dirty_git: bool = False
    claude: dict[str, JsonValue] = field(default_factory=_empty_json_dict)
    codex: dict[str, JsonValue] = field(default_factory=_empty_json_dict)
    args: dict[str, JsonValue] = field(default_factory=_empty_json_dict)

    def agent_options(self, agent: AgentName) -> dict[str, JsonValue]:
        """Return provider-specific options for an agent."""

        return self.claude if agent == "claude" else self.codex

    def as_prompt_dict(self) -> dict[str, JsonValue]:
        """Return JSON-like metadata safe to include in rendered prompts."""

        payload: dict[str, JsonValue] = {
            "mode": self.mode,
            "workspace": self.workspace,
            "requires_clean_git": self.requires_clean_git,
            "allow_dirty_git": self.allow_dirty_git,
        }
        if self.name is not None:
            payload["name"] = self.name
        if self.description is not None:
            payload["description"] = self.description
        if self.default_agent is not None:
            payload["default_agent"] = self.default_agent
        if self.args:
            payload["args"] = self.args
        return payload


@dataclass(frozen=True, slots=True)
class SourceParts:
    """Physical source split into metadata prefix and pseudocode body."""

    shebang: str | None
    frontmatter: str | None
    body: str
    body_start_line: int

    @property
    def prefix(self) -> str:
        """Return the shebang/frontmatter prefix exactly enough to reassemble source."""

        parts: list[str] = []
        if self.shebang is not None:
            parts.append(self.shebang)
        if self.frontmatter is not None:
            parts.append("---\n" + self.frontmatter + "---\n")
        return "".join(parts)


def parse_executable_file(path: Path) -> ExecutableScript:
    """Parse an executable Agent Pseudocode script from disk."""

    text = path.read_text(encoding="utf-8")
    parts = split_source_parts(text)
    return ExecutableScript(
        path=path,
        shebang=parts.shebang,
        frontmatter=parts.frontmatter,
        body=parts.body,
        body_start_line=parts.body_start_line,
        metadata=parse_metadata(parts.frontmatter),
    )


def split_source_parts(text: str) -> SourceParts:
    """Split optional shebang/frontmatter from a pseudocode source body.

    Supported executable envelope::

        #!/usr/bin/env apseudo-run
        ---
        name: example
        default_agent: codex
        ---

        process example():
            return Accepted(reason="ok")
    """

    lines = text.splitlines(keepends=True)
    index = 0
    body_start_line = 1
    shebang: str | None = None
    frontmatter: str | None = None

    if lines and lines[0].startswith("#!"):
        shebang = lines[0]
        index = 1
        body_start_line = 2

    if index < len(lines) and lines[index].strip() == "---":
        frontmatter_start = index + 1
        closing_index: int | None = None
        for candidate in range(frontmatter_start, len(lines)):
            if lines[candidate].strip() == "---":
                closing_index = candidate
                break
        if closing_index is not None:
            frontmatter = "".join(lines[frontmatter_start:closing_index])
            index = closing_index + 1
            body_start_line = index + 1

    return SourceParts(
        shebang=shebang,
        frontmatter=frontmatter,
        body="".join(lines[index:]),
        body_start_line=body_start_line,
    )


def parse_metadata(frontmatter: str | None) -> ScriptMetadata:
    """Parse the runner frontmatter subset."""

    data = parse_simple_frontmatter(frontmatter or "")
    default_agent = _agent_or_none(data.get("default_agent"))
    mode = _mode_or_default(data.get("mode"), "plan")
    workspace_raw = data.get("workspace", "git_root")
    workspace = workspace_raw if isinstance(workspace_raw, str) else "git_root"
    return ScriptMetadata(
        name=_str_or_none(data.get("name")),
        description=_str_or_none(data.get("description")),
        default_agent=default_agent,
        mode=mode,
        workspace=workspace,
        requires_clean_git=_bool_or_default(data.get("requires_clean_git"), False),
        allow_dirty_git=_bool_or_default(data.get("allow_dirty_git"), False),
        claude=_dict_or_empty(data.get("claude")),
        codex=_dict_or_empty(data.get("codex")),
        args=_dict_or_empty(data.get("args")),
    )


def parse_simple_frontmatter(text: str) -> dict[str, JsonValue]:
    """Parse a small YAML-like frontmatter subset without external dependencies.

    This parser intentionally supports only the shapes used by runner metadata:
    top-level ``key: value`` pairs, one-level nested provider maps, and simple
    ``- item`` lists. It is not a general YAML parser.
    """

    root: dict[str, JsonValue] = {}
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        raw = lines[index]
        if _is_ignorable_frontmatter_line(raw):
            index += 1
            continue
        indent = _indent(raw)
        if indent != 0:
            index += 1
            continue
        key, value_text = _split_key_value(raw.strip())
        if key is None:
            index += 1
            continue
        if value_text:
            root[key] = _parse_scalar(value_text)
            index += 1
            continue

        nested_lines: list[str] = []
        index += 1
        while index < len(lines):
            candidate = lines[index]
            if candidate.strip() and _indent(candidate) == 0:
                break
            nested_lines.append(candidate)
            index += 1
        root[key] = _parse_nested_block(nested_lines)
    return root


def serialize_frontmatter(data: Mapping[str, JsonValue]) -> str:
    """Serialize a JSON-like mapping to the supported frontmatter subset."""

    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            lines.extend(_serialize_nested(value, indent=2))
        elif isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {_format_scalar(item)}")
        else:
            lines.append(f"{key}: {_format_scalar(value)}")
    return "\n".join(lines).rstrip() + "\n"


def _parse_nested_block(lines: Iterable[str]) -> JsonValue:
    useful = [line for line in lines if not _is_ignorable_frontmatter_line(line)]
    if not useful:
        return {}
    if all(line.lstrip().startswith("-") for line in useful):
        return [_parse_scalar(line.lstrip()[1:].strip()) for line in useful]
    result: dict[str, JsonValue] = {}
    index = 0
    while index < len(useful):
        stripped = useful[index].strip()
        key, value_text = _split_key_value(stripped)
        if key is None:
            index += 1
            continue
        if value_text:
            result[key] = _parse_scalar(value_text)
            index += 1
            continue
        nested: list[str] = []
        index += 1
        while index < len(useful) and _indent(useful[index]) > 2:
            nested.append(useful[index][2:])
            index += 1
        result[key] = _parse_nested_block(nested)
    return result


def _serialize_nested(data: Mapping[str, JsonValue], *, indent: int) -> list[str]:
    prefix = " " * indent
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.extend(_serialize_nested(value, indent=indent + 2))
        elif isinstance(value, list):
            lines.append(f"{prefix}{key}:")
            for item in value:
                lines.append(f"{prefix}  - {_format_scalar(item)}")
        else:
            lines.append(f"{prefix}{key}: {_format_scalar(value)}")
    return lines


def _split_key_value(line: str) -> tuple[str | None, str]:
    if not line or line.startswith("#") or ":" not in line:
        return None, ""
    key, value = line.split(":", 1)
    key = key.strip()
    if not key:
        return None, ""
    return key, value.strip()


def _parse_scalar(value: str) -> JsonValue:
    text = _strip_inline_comment(value).strip()
    if text == "":
        return ""
    lowered = text.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered in {"null", "none", "~"}:
        return None
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part.strip()) for part in inner.split(",")]
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _format_scalar(value: JsonValue) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_format_scalar(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{}"
    text = str(value)
    if text == "" or any(char in text for char in [":", "#", "[", "]", "{", "}"]):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def _strip_inline_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            continue
        if char == "#" and (index == 0 or value[index - 1].isspace()):
            return value[:index]
    return value


def _is_ignorable_frontmatter_line(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def _indent(line: str) -> int:
    expanded = line.expandtabs(2)
    return len(expanded) - len(expanded.lstrip(" "))


def _agent_or_none(value: JsonValue | None) -> AgentName | None:
    if isinstance(value, str) and value in VALID_AGENTS:
        return cast(AgentName, value)
    return None


def _mode_or_default(value: JsonValue | None, default: RunMode) -> RunMode:
    if isinstance(value, str) and value in VALID_MODES:
        return cast(RunMode, value)
    return default


def _str_or_none(value: JsonValue | None) -> str | None:
    return value if isinstance(value, str) else None


def _bool_or_default(value: JsonValue | None, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _dict_or_empty(value: JsonValue | None) -> dict[str, JsonValue]:
    if isinstance(value, dict):
        return dict(value)
    return {}
