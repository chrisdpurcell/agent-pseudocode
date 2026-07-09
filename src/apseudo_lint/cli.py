"""Command-line interface for apseudo-lint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .discover import discover_changed_paths
from .extract import collect_paths, extract_markdown_fences
from .lint import lint_paths, lint_snippet
from .model import Diagnostic, LintConfig, Severity, Snippet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apseudo-lint",
        description="Validate Pythonic Agent Pseudocode in .apseudo files and Markdown fenced blocks.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to lint. Defaults to current directory.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Explicit .apseudo-lint.toml, apseudo.toml, or pyproject.toml file.",
    )
    parser.add_argument(
        "--format", choices=("text", "json", "github"), default="text", help="Output format."
    )
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Treat warnings as failures without other strict behavior.",
    )
    parser.add_argument(
        "--errors-only",
        action="store_true",
        help="Suppress warnings and infos in output/failure calculation.",
    )
    parser.add_argument(
        "--changed", action="store_true", help="Lint only Git-changed supported files."
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress success output.")
    parser.add_argument(
        "--stdin-filename", type=Path, default=None, help="Lint stdin as if it came from this path."
    )
    parser.add_argument("--version", action="version", version=f"apseudo-lint {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    start = args.paths[0] if args.paths else Path.cwd()
    try:
        config = load_config(start=start, explicit=args.config)
    except Exception as exc:
        print(f"apseudo-lint: failed to load config: {exc}", file=sys.stderr)
        return 2
    if args.strict:
        config.strict = True
    if args.fail_on_warnings:
        config.fail_on_warning = True

    if args.stdin_filename:
        diagnostics = _lint_stdin(args.stdin_filename, sys.stdin.read(), config)
        paths = [args.stdin_filename]
    elif args.changed:
        paths = discover_changed_paths(config)
        diagnostics = lint_paths(paths, config) if paths else []
    else:
        paths = collect_paths(args.paths, config)
        diagnostics = lint_paths(paths, config)

    if args.errors_only:
        diagnostics = [diag for diag in diagnostics if diag.severity == Severity.ERROR]

    if config.strict:
        diagnostics = [
            _as_error(diag) if diag.severity == Severity.WARNING else diag for diag in diagnostics
        ]

    failure_count = sum(1 for diag in diagnostics if config.should_fail_on(diag.severity))

    if args.format == "json":
        _print_json(paths, diagnostics, failure_count)
    elif args.format == "github":
        _print_github(paths, diagnostics, failure_count, quiet=args.quiet)
    else:
        _print_text(paths, diagnostics, failure_count, quiet=args.quiet)

    return 1 if failure_count else 0


def _lint_stdin(path: Path, text: str, config: LintConfig) -> list[Diagnostic]:
    if path.suffix.lower() in config.markdown_extensions:
        diagnostics: list[Diagnostic] = []
        for snippet in extract_markdown_fences(path, text, config):
            diagnostics.extend(lint_snippet(snippet, config))
        return diagnostics
    return lint_snippet(Snippet(path=path, text=text, start_line=1, name="stdin"), config)


def _as_error(diag: Diagnostic) -> Diagnostic:
    return Diagnostic(
        diag.path,
        diag.line,
        diag.column,
        diag.code,
        Severity.ERROR,
        diag.message,
        diag.hint,
        diag.snippet_name,
    )


def _print_json(paths: list[Path], diagnostics: list[Diagnostic], failure_count: int) -> None:
    counts = {"error": 0, "warning": 0, "info": 0}
    for diag in diagnostics:
        counts[diag.severity.value] += 1
    payload = {
        "tool": "apseudo-lint",
        "version": __version__,
        "paths": [str(path) for path in paths],
        "summary": {
            "files_checked": len(paths),
            "diagnostics": len(diagnostics),
            "failures": failure_count,
            **counts,
        },
        "diagnostics": [diag.as_dict() for diag in diagnostics],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_github(
    paths: list[Path], diagnostics: list[Diagnostic], failure_count: int, *, quiet: bool
) -> None:
    if diagnostics:
        for diag in diagnostics:
            print(diag.format_github())
        print(
            f"apseudo-lint: checked {len(paths)} file(s); {len(diagnostics)} diagnostic(s); {failure_count} failure(s)."
        )
        return
    if not quiet:
        print(f"apseudo-lint: checked {len(paths)} file(s); no diagnostics.")


def _print_text(
    paths: list[Path], diagnostics: list[Diagnostic], failure_count: int, *, quiet: bool
) -> None:
    if diagnostics:
        for diag in diagnostics:
            print(diag.format_text())
        print(
            f"apseudo-lint: checked {len(paths)} file(s); {len(diagnostics)} diagnostic(s); {failure_count} failure(s)."
        )
        return
    if not quiet:
        print(f"apseudo-lint: checked {len(paths)} file(s); no diagnostics.")


if __name__ == "__main__":
    raise SystemExit(main())
