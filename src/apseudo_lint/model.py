"""Data model for agent pseudocode diagnostics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


class Severity(StrEnum):
    """Diagnostic severity."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A single linter finding."""

    path: Path
    line: int
    column: int
    code: str
    severity: Severity
    message: str
    hint: str | None = None
    snippet_name: str | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "path": str(self.path),
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
        }
        if self.hint:
            payload["hint"] = self.hint
        if self.snippet_name:
            payload["snippet"] = self.snippet_name
        return payload

    def format_text(self) -> str:
        location = f"{self.path}:{self.line}:{self.column}"
        body = f"{location}: {self.severity.value.upper()} {self.code}: {self.message}"
        if self.hint:
            body += f"\n  hint: {self.hint}"
        if self.snippet_name:
            body += f"\n  block: {self.snippet_name}"
        return body

    def format_github(self) -> str:
        level = "error" if self.severity == Severity.ERROR else "warning"
        message = f"{self.code}: {self.message}"
        if self.hint:
            message += f" Hint: {self.hint}"
        escaped_message = _gha_escape_data(message)
        escaped_path = _gha_escape_meta(str(self.path))
        return (
            f"::{level} file={escaped_path},line={self.line},col={self.column},"
            f"title={self.code}::{escaped_message}"
        )


@dataclass(frozen=True, slots=True)
class Snippet:
    """A standalone pseudocode source or a pseudocode fenced block inside Markdown."""

    path: Path
    text: str
    start_line: int = 1
    name: str | None = None
    language: str | None = None

    def to_source_line(self, local_line: int) -> int:
        return self.start_line + local_line - 1


@dataclass(slots=True)
class LintConfig:
    """Configurable linter behavior."""

    max_nesting: int = 4
    strict: bool = False
    fail_on_warning: bool = False
    require_process_declaration: bool = False
    require_verification_after_mutation: bool = False
    allowed_outcomes: set[str] = field(
        default_factory=lambda: {
            "Accepted",
            "Approved",
            "Blocked",
            "Deferred",
            "Failed",
            "NeedsInput",
            "NeedsUserDecision",
            "OpenIssue",
            "Rejected",
            "Skipped",
        }
    )
    markdown_fence_languages: set[str] = field(
        default_factory=lambda: {
            "apseudo",
            "agent-pseudocode",
            "agent_pseudocode",
            "agentpseudo",
            "py-pseudocode",
            "python-pseudocode",
            "pythonic-pseudocode",
            "pseudocode-python",
            "pseudocode-pythonic",
        }
    )
    file_extensions: set[str] = field(
        default_factory=lambda: {".apseudo", ".agentpseudo", ".pseudocode"}
    )
    markdown_extensions: set[str] = field(default_factory=lambda: {".md", ".markdown", ".mdown"})
    exclude: list[str] = field(
        default_factory=lambda: [
            ".git",
            ".hg",
            ".svn",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".venv",
            "__pycache__",
            "node_modules",
            "dist",
            "build",
        ]
    )
    ignore_codes: set[str] = field(default_factory=lambda: set[str]())

    def should_fail_on(self, severity: Severity) -> bool:
        if severity == Severity.ERROR:
            return True
        return severity == Severity.WARNING and (self.strict or self.fail_on_warning)


def _gha_escape_data(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _gha_escape_meta(value: str) -> str:
    return _gha_escape_data(value).replace(":", "%3A").replace(",", "%2C")
