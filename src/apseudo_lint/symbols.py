"""Symbol extraction and lightweight navigation helpers for Agent Pseudocode."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .extract import extract_markdown_fences
from .model import LintConfig

PROCESS_RE = re.compile(r"^(?P<indent>\s*)(?:process|def)\s+(?P<name>[A-Za-z_]\w*)\s*\(")
CALL_RE = re.compile(r"(?<![.\w])(?P<name>[A-Za-z_]\w*)\s*\(")
TOKEN_RE = re.compile(r"@?[A-Za-z_][A-Za-z0-9_]*(?:-[A-Za-z0-9_]+)*")
CONTROL_NAMES = {
    "if",
    "elif",
    "else",
    "while",
    "for",
    "in",
    "return",
    "continue",
    "break",
    "try",
    "except",
    "finally",
    "with",
    "process",
    "def",
}


@dataclass(frozen=True, slots=True)
class Range:
    """Zero-based LSP-style text range."""

    start_line: int
    start_character: int
    end_line: int
    end_character: int

    def as_lsp(self) -> dict[str, dict[str, int]]:
        """Return an LSP range object."""

        return {
            "start": {"line": self.start_line, "character": self.start_character},
            "end": {"line": self.end_line, "character": self.end_character},
        }


@dataclass(frozen=True, slots=True)
class Symbol:
    """A process symbol found in source."""

    name: str
    kind: str
    range: Range
    selection_range: Range
    container_name: str | None = None


@dataclass(frozen=True, slots=True)
class Occurrence:
    """A token occurrence found in source."""

    name: str
    range: Range


def document_symbols(text: str, *, base_line: int = 0) -> list[Symbol]:
    """Return process symbols in one pseudocode buffer."""

    symbols: list[Symbol] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = PROCESS_RE.match(line)
        if match is None:
            continue
        name = match.group("name")
        start = match.start("name")
        end = match.end("name")
        full_range = _block_range(lines, index, base_line=base_line)
        selection = Range(base_line + index, start, base_line + index, end)
        symbols.append(
            Symbol(name=name, kind="process", range=full_range, selection_range=selection)
        )
    return symbols


def markdown_document_symbols(path: Path, text: str, config: LintConfig) -> list[Symbol]:
    """Return process symbols from supported Markdown fenced blocks."""

    symbols: list[Symbol] = []
    for snippet in extract_markdown_fences(path, text, config):
        base_line = max(0, snippet.start_line - 1)
        symbols.extend(document_symbols(snippet.text, base_line=base_line))
    return symbols


def token_range_at_position(text: str, line: int, character: int) -> Occurrence | None:
    """Return the token occurrence at a zero-based position."""

    lines = text.splitlines()
    if line < 0 or line >= len(lines):
        return None
    current = lines[line]
    character = max(0, min(character, len(current)))
    for match in TOKEN_RE.finditer(current):
        if match.start() <= character <= match.end():
            return Occurrence(
                name=match.group(0),
                range=Range(line, match.start(), line, match.end()),
            )
    return None


def occurrences(text: str, token: str) -> list[Occurrence]:
    """Return all exact token occurrences in text."""

    if not token or token in CONTROL_NAMES:
        return []
    result: list[Occurrence] = []
    pattern = re.compile(rf"(?<![A-Za-z0-9_@-]){re.escape(token)}(?![A-Za-z0-9_-])")
    for line_index, line in enumerate(text.splitlines()):
        for match in pattern.finditer(line):
            result.append(
                Occurrence(
                    name=token,
                    range=Range(line_index, match.start(), line_index, match.end()),
                )
            )
    return result


def definition_for_token(text: str, token: str) -> Symbol | None:
    """Return the first process definition matching token in a buffer."""

    for symbol in document_symbols(text):
        if symbol.name == token:
            return symbol
    return None


def _block_range(lines: list[str], header_index: int, *, base_line: int) -> Range:
    header = lines[header_index]
    indent = len(header) - len(header.lstrip(" "))
    end_index = header_index
    for candidate_index in range(header_index + 1, len(lines)):
        candidate = lines[candidate_index]
        if not candidate.strip():
            end_index = candidate_index
            continue
        candidate_indent = len(candidate) - len(candidate.lstrip(" "))
        if candidate_indent <= indent:
            break
        end_index = candidate_index
    end_character = len(lines[end_index]) if end_index < len(lines) else 0
    return Range(base_line + header_index, 0, base_line + end_index, end_character)
