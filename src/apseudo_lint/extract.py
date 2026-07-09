"""Source extraction for standalone pseudocode and Markdown fenced blocks."""

from __future__ import annotations

import re
from pathlib import Path

from .executable import split_source_parts
from .model import LintConfig, Snippet

FENCE_RE = re.compile(r"^(?P<indent>[ \t]*)(?P<fence>`{3,}|~{3,})(?P<info>.*)$")


def is_lintable_path(path: Path, config: LintConfig | None = None) -> bool:
    """Return true when a path is a supported source or Markdown file."""

    effective = config or LintConfig()
    supported = effective.file_extensions | effective.markdown_extensions
    return path.suffix.lower() in supported


def collect_paths(paths: list[Path], config: LintConfig | None = None) -> list[Path]:
    """Expand files/directories to lintable file paths."""

    effective = config or LintConfig()
    if not paths:
        paths = [Path.cwd()]

    result: list[Path] = []
    seen: set[Path] = set()
    for raw_path in paths:
        path = raw_path.expanduser()
        if not path.exists():
            if path not in seen:
                result.append(path)
                seen.add(path)
            continue
        if path.is_file():
            if _is_excluded(path, effective):
                continue
            if is_lintable_path(path, effective) and path not in seen:
                result.append(path)
                seen.add(path)
            continue
        if path.is_dir():
            for child in path.rglob("*"):
                if _is_excluded(child, effective):
                    continue
                if child.is_file() and is_lintable_path(child, effective) and child not in seen:
                    result.append(child)
                    seen.add(child)
    return sorted(result)


def extract_snippets(path: Path, config: LintConfig) -> list[Snippet]:
    """Extract lintable pseudocode snippets from a file."""

    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in config.file_extensions:
        parts = split_source_parts(text)
        return [
            Snippet(
                path=path,
                text=parts.body,
                start_line=parts.body_start_line,
                name=path.name,
                language=suffix[1:],
            )
        ]
    if suffix in config.markdown_extensions:
        return extract_markdown_fences(path, text, config)
    return []


def extract_markdown_fences(path: Path, text: str, config: LintConfig) -> list[Snippet]:
    """Extract fenced pseudocode blocks from Markdown."""

    snippets: list[Snippet] = []
    lines = text.splitlines(keepends=True)
    in_fence = False
    marker = ""
    lang = ""
    start_line = 1
    buffer: list[str] = []
    skip_next = False
    skip_current = False
    index = 0

    for line_no, line in enumerate(lines, start=1):
        stripped = line.rstrip("\n")
        if not in_fence:
            if "apseudo-lint: disable-next-fence" in stripped:
                skip_next = True
                continue
            match = FENCE_RE.match(stripped)
            if not match:
                continue
            candidate_lang = _language(match.group("info"))
            if candidate_lang not in config.markdown_fence_languages:
                continue
            in_fence = True
            marker = match.group("fence")
            lang = candidate_lang
            start_line = line_no + 1
            buffer = []
            skip_current = skip_next
            skip_next = False
            continue

        closing_prefix = marker[0] * len(marker)
        if stripped.lstrip().startswith(closing_prefix):
            if not skip_current:
                index += 1
                snippets.append(
                    Snippet(
                        path=path,
                        text="".join(buffer),
                        start_line=start_line,
                        name=f"{lang} fence {index}",
                        language=lang,
                    )
                )
            in_fence = False
            marker = ""
            lang = ""
            buffer = []
            skip_current = False
        else:
            buffer.append(line)

    if in_fence and not skip_current:
        index += 1
        snippets.append(
            Snippet(
                path=path,
                text="".join(buffer),
                start_line=start_line,
                name=f"unterminated {lang} fence {index}",
                language=lang,
            )
        )
    return snippets


def extract_blocks(path: Path, config: LintConfig) -> list[Snippet]:
    """Backward-compatible alias for extracting snippets from a file."""

    return extract_snippets(path, config)


def _language(info: str) -> str:
    if not info.strip():
        return ""
    first = info.strip().split(maxsplit=1)[0].strip("{}")
    return first[1:].lower() if first.startswith(".") else first.lower()


def _is_excluded(path: Path, config: LintConfig) -> bool:
    normalized = path.as_posix()
    parts = set(path.parts)
    for pattern in config.exclude:
        cleaned = pattern.strip()
        if not cleaned:
            continue
        if cleaned in parts or cleaned in normalized:
            return True
    return False
