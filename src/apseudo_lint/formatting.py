"""Formatter for Pythonic Agent Pseudocode.

The formatter is intentionally conservative. It normalizes whitespace and small
style details while avoiding semantic rewrites. The linter remains the source of
truth for correctness; formatting should make pseudocode easier to read, not
silently repair ambiguous process logic.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .executable import split_source_parts
from .extract import FENCE_RE
from .model import LintConfig

CONTROL_KEYWORD_RE = re.compile(
    r"^(?P<kw>IF|ELIF|ELSE|WHILE|FOR|RETURN|CONTINUE|BREAK|PROCESS|DEF|TRY|EXCEPT|FINALLY|WITH|RAISE|PASS)\b",
    re.IGNORECASE,
)
NORMATIVE_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bmust\s+not\b", re.IGNORECASE), "MUST NOT"),
    (re.compile(r"\bshould\s+not\b", re.IGNORECASE), "SHOULD NOT"),
    (re.compile(r"\bmust\b", re.IGNORECASE), "MUST"),
    (re.compile(r"\bshould\b", re.IGNORECASE), "SHOULD"),
    (re.compile(r"\bmay\b", re.IGNORECASE), "MAY"),
    (re.compile(r"\brequired\b", re.IGNORECASE), "REQUIRED"),
    (re.compile(r"\boptional\b", re.IGNORECASE), "OPTIONAL"),
)
COMPOUND_OPERATORS_RE = re.compile(r"\s*(==|!=|<=|>=|\+=|-=|\*=|/=|//=|%=|:=|->|=>)\s*")
SINGLE_EQUALS_RE = re.compile(r"(?<![<>=!:+\-*/%])\s*=\s*(?![=>])")
COMPARE_RE = re.compile(r"(?<![<>=\-])\s*([<>])\s*(?![<>=])")
COMMA_RE = re.compile(r",\s*")
MULTISPACE_RE = re.compile(r" {2,}")
HEADER_COLON_RE = re.compile(r"\s+:")
PROCESS_SPACE_RE = re.compile(r"\b(process|def)\s+([A-Za-z_]\w*)\s+\(")
KEYWORD_SPACE_RE = re.compile(r"\b(if|elif|while|for|return)\s+")
ELSE_SPACE_RE = re.compile(r"\b(else|try|finally)\s+:")
PROCESS_HEADER_RE = re.compile(
    r"^(process|def)\s+([A-Za-z_]\w*)\s*\((?P<args>.*?)\)\s*(?P<ret>->\s*[^:]+)?\s*:$"
)
IF_HEADER_RE = re.compile(r"^(if|elif|while)\s+(.+):$")
FOR_HEADER_RE = re.compile(r"^for\s+(.+?)\s+in\s+(.+):$")


@dataclass(frozen=True, slots=True)
class FormatOptions:
    """Formatter knobs shared by the CLI and language server."""

    indent_size: int = 4
    max_blank_lines: int = 1
    final_newline: bool = True
    normalize_keywords: bool = True
    uppercase_normative: bool = True
    normalize_operator_spacing: bool = True
    normalize_comment_spacing: bool = True
    round_indentation: bool = True


@dataclass(frozen=True, slots=True)
class FormatResult:
    """Result from formatting a file or text buffer."""

    original: str
    formatted: str

    @property
    def changed(self) -> bool:
        return self.original != self.formatted

    def unified_diff(self, path: Path | str) -> str:
        label = str(path)
        return "".join(
            difflib.unified_diff(
                self.original.splitlines(keepends=True),
                self.formatted.splitlines(keepends=True),
                fromfile=f"{label}\tbefore",
                tofile=f"{label}\tafter",
            )
        )


def format_file(
    path: Path, config: LintConfig, options: FormatOptions | None = None
) -> FormatResult:
    """Format a supported file's content without writing it."""

    original = path.read_text(encoding="utf-8")
    return format_text(original, path=path, config=config, options=options)


def format_text(
    text: str,
    *,
    path: Path | None,
    config: LintConfig,
    options: FormatOptions | None = None,
) -> FormatResult:
    """Format standalone pseudocode text or Markdown pseudocode fences."""

    effective = options or FormatOptions()
    suffix = path.suffix.lower() if path is not None else ""
    if suffix in config.markdown_extensions:
        formatted = format_markdown_fences(text, config=config, options=effective)
    else:
        formatted = format_standalone_source(text, options=effective)
    return FormatResult(original=text, formatted=formatted)


def format_markdown_fences(text: str, *, config: LintConfig, options: FormatOptions) -> str:
    """Format only supported pseudocode fenced code blocks inside Markdown."""

    lines = text.splitlines(keepends=True)
    output: list[str] = []
    buffer: list[str] = []
    in_fence = False
    marker = ""
    should_format = False

    for line in lines:
        line_without_newline = line.rstrip("\n")
        stripped = line_without_newline.rstrip("\r")
        if not in_fence:
            match = FENCE_RE.match(stripped)
            if match is None:
                output.append(line)
                continue
            language = _language(match.group("info"))
            in_fence = True
            marker = match.group("fence")
            should_format = language in config.markdown_fence_languages
            output.append(line)
            buffer = []
            continue

        closing_prefix = marker[0] * len(marker)
        if stripped.lstrip().startswith(closing_prefix):
            if should_format:
                output.append(format_pseudocode_source("".join(buffer), options=options))
            else:
                output.extend(buffer)
            output.append(line)
            in_fence = False
            marker = ""
            should_format = False
            buffer = []
            continue

        buffer.append(line)

    if in_fence:
        if should_format:
            output.append(format_pseudocode_source("".join(buffer), options=options))
        else:
            output.extend(buffer)

    return "".join(output)


def format_standalone_source(text: str, *, options: FormatOptions | None = None) -> str:
    """Format standalone pseudocode while preserving shebang/frontmatter metadata."""

    parts = split_source_parts(text)
    formatted_body = format_pseudocode_source(parts.body, options=options)
    return parts.prefix + formatted_body


def format_pseudocode_source(text: str, *, options: FormatOptions | None = None) -> str:
    """Format standalone pseudocode text."""

    effective = options or FormatOptions()
    raw_lines = text.splitlines()
    formatted_lines: list[str] = []
    blank_run = 0

    for raw_line in raw_lines:
        formatted = _format_line(raw_line, effective)
        if formatted == "":
            blank_run += 1
            if blank_run <= effective.max_blank_lines:
                formatted_lines.append("")
            continue
        blank_run = 0
        formatted_lines.append(formatted)

    while formatted_lines and formatted_lines[-1] == "":
        formatted_lines.pop()

    result = "\n".join(formatted_lines)
    if effective.final_newline:
        result += "\n"
    return result


def _format_line(line: str, options: FormatOptions) -> str:
    expanded = line.expandtabs(options.indent_size).rstrip()
    if not expanded.strip():
        return ""

    leading = len(expanded) - len(expanded.lstrip(" "))
    indent = _normalize_indent(leading, options)
    body = expanded.lstrip(" ")
    code, comment = _split_comment(body)

    if code.strip():
        formatted_code = _format_code(code.strip(), options)
        if comment:
            formatted_comment = _format_comment(comment.strip(), options)
            separator = "  " if options.normalize_comment_spacing else " "
            return f"{indent}{formatted_code}{separator}{formatted_comment}"
        return f"{indent}{formatted_code}"

    if comment:
        return f"{indent}{_format_comment(comment.strip(), options)}"
    return ""


def _normalize_indent(leading_spaces: int, options: FormatOptions) -> str:
    if not options.round_indentation or leading_spaces == 0:
        return " " * leading_spaces
    level_width = (
        (leading_spaces + options.indent_size - 1) // options.indent_size
    ) * options.indent_size
    return " " * level_width


def _format_code(code: str, options: FormatOptions) -> str:
    result = code.strip()
    if options.normalize_keywords:
        result = CONTROL_KEYWORD_RE.sub(lambda match: match.group("kw").lower(), result)
    if options.normalize_operator_spacing:
        result = _format_non_string_segments(result, _format_spacing_segment)
    result = HEADER_COLON_RE.sub(":", result).strip()
    result = _normalize_keyword_argument_spacing(result)

    process_match = PROCESS_HEADER_RE.match(result)
    if process_match is not None:
        args = _normalize_argument_list(process_match.group("args"))
        ret = process_match.group("ret")
        ret_text = f" {ret.strip()}" if ret else ""
        return f"{process_match.group(1)} {process_match.group(2)}({args}){ret_text}:"

    if_match = IF_HEADER_RE.match(result)
    if if_match is not None:
        return f"{if_match.group(1)} {if_match.group(2).strip()}:"

    for_match = FOR_HEADER_RE.match(result)
    if for_match is not None:
        return f"for {for_match.group(1).strip()} in {for_match.group(2).strip()}:"

    result = PROCESS_SPACE_RE.sub(lambda match: f"{match.group(1)} {match.group(2)}(", result)
    result = KEYWORD_SPACE_RE.sub(lambda match: f"{match.group(1)} ", result)
    result = ELSE_SPACE_RE.sub(lambda match: f"{match.group(1)}:", result)
    return result.strip()


def _normalize_argument_list(args: str) -> str:
    return ", ".join(part.strip() for part in args.split(",") if part.strip())


def _normalize_keyword_argument_spacing(code: str) -> str:
    if "(" not in code or ")" not in code:
        return code
    result = re.sub(r"(?<=\()\s*([A-Za-z_]\w*)\s=\s", r"\1=", code)
    return re.sub(r",\s*([A-Za-z_]\w*)\s=\s", r", \1=", result)


def _format_spacing_segment(segment: str) -> str:
    if not segment:
        return segment
    result = COMMA_RE.sub(", ", segment)
    result = COMPOUND_OPERATORS_RE.sub(r" \1 ", result)
    result = SINGLE_EQUALS_RE.sub(" = ", result)
    result = COMPARE_RE.sub(r" \1 ", result)
    result = HEADER_COLON_RE.sub(":", result)
    result = MULTISPACE_RE.sub(" ", result)
    return _normalize_parenthesized_spacing(result)


def _normalize_parenthesized_spacing(text: str) -> str:
    # Keep call signatures Pythonic: `name(arg, key="value")`, while leaving
    # assignment statements such as `round = 1` alone. This intentionally handles
    # simple, non-nested argument lists; nested calls are processed from innermost
    # outward by the repeated substitution.
    pattern = re.compile(r"\((?P<body>[^()]*)\)")

    def replace(match: re.Match[str]) -> str:
        body = match.group("body").strip()
        body = re.sub(r"\b([A-Za-z_]\w*)\s+=\s+", r"\1=", body)
        body = COMMA_RE.sub(", ", body)
        return f"({body})"

    previous = None
    result = text
    while previous != result:
        previous = result
        result = pattern.sub(replace, result)
    return result


def _format_comment(comment: str, options: FormatOptions) -> str:
    result = comment if comment.startswith("#") else f"# {comment}"
    if result.startswith("#") and len(result) > 1 and not result.startswith("# "):
        result = "# " + result[1:].lstrip()
    if options.uppercase_normative:
        for pattern, replacement in NORMATIVE_REPLACEMENTS:
            result = pattern.sub(replacement, result)
    return result.rstrip()


def _format_non_string_segments(text: str, formatter: Callable[[str], str]) -> str:
    parts: list[str] = []
    cursor = 0
    quote: str | None = None
    escaped = False
    segment_start = 0

    while cursor < len(text):
        char = text[cursor]
        if escaped:
            escaped = False
            cursor += 1
            continue
        if char == "\\":
            escaped = True
            cursor += 1
            continue
        if quote is not None:
            if char == quote:
                quote = None
            cursor += 1
            continue
        if char in {'"', "'"}:
            if segment_start < cursor:
                parts.append(formatter(text[segment_start:cursor]))
            string_start = cursor
            quote = char
            cursor += 1
            while cursor < len(text):
                inner = text[cursor]
                if inner == "\\":
                    cursor += 2
                    continue
                if inner == char:
                    cursor += 1
                    break
                cursor += 1
            parts.append(text[string_start:cursor])
            segment_start = cursor
            quote = None
            continue
        cursor += 1

    if segment_start < len(text):
        parts.append(formatter(text[segment_start:]))
    return "".join(parts)


def _split_comment(line: str) -> tuple[str, str]:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(line):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote is not None:
            if char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
            continue
        if char == "#":
            return line[:index], line[index:]
    return line, ""


def _language(info: str) -> str:
    if not info.strip():
        return ""
    first = info.strip().split(maxsplit=1)[0].strip("{}")
    return first[1:].lower() if first.startswith(".") else first.lower()
