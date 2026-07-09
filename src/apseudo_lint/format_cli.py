"""Command-line interface for apseudo-format."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .discover import discover_changed_paths
from .extract import collect_paths
from .formatting import FormatOptions, format_file, format_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apseudo-format",
        description="Format Pythonic Agent Pseudocode in .apseudo files and Markdown fenced blocks.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Files or directories to format. Defaults to current directory.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Explicit .apseudo-lint.toml, apseudo.toml, or pyproject.toml file.",
    )
    parser.add_argument("--check", action="store_true", help="Exit non-zero if files need formatting.")
    parser.add_argument("--diff", action="store_true", help="Print unified diffs for changed files.")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write formatted output. This is the default unless --check or --diff is used.",
    )
    parser.add_argument(
        "--stdin-filename",
        type=Path,
        default=None,
        help="Format stdin as if it came from this path and write formatted text to stdout.",
    )
    parser.add_argument("--indent-size", type=int, default=4, help="Indent width in spaces.")
    parser.add_argument(
        "--max-blank-lines", type=int, default=2, help="Maximum consecutive blank lines."
    )
    parser.add_argument(
        "--round-indentation",
        action="store_true",
        help="Round leading indentation to multiples of --indent-size. Off by default to avoid unsafe reindentation.",
    )
    parser.add_argument(
        "--no-uppercase-normative",
        action="store_true",
        help="Do not uppercase MUST/SHOULD/MAY-style normative keywords in comments.",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress success output.")
    parser.add_argument("--changed", action="store_true", help="Format only Git-changed supported files.")
    parser.add_argument("--version", action="version", version=f"apseudo-format {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = FormatOptions(
        indent_size=max(1, args.indent_size),
        max_blank_lines=max(0, args.max_blank_lines),
        uppercase_normative=not args.no_uppercase_normative,
        round_indentation=args.round_indentation,
    )
    start = args.stdin_filename or (args.paths[0] if args.paths else Path.cwd())

    try:
        config = load_config(start=start, explicit=args.config)
    except Exception as exc:
        print(f"apseudo-format: failed to load config: {exc}", file=sys.stderr)
        return 2

    if args.stdin_filename is not None:
        result = format_text(sys.stdin.read(), path=args.stdin_filename, config=config, options=options)
        sys.stdout.write(result.formatted)
        return 0

    paths = discover_changed_paths(config) if args.changed else collect_paths(args.paths, config)
    changed: list[tuple[Path, str]] = []
    write = args.write or not (args.check or args.diff)

    for path in paths:
        if not path.exists() or not path.is_file():
            print(f"apseudo-format: file does not exist: {path}", file=sys.stderr)
            return 2
        result = format_file(path, config, options)
        if not result.changed:
            continue
        if args.diff:
            changed.append((path, result.unified_diff(path)))
        else:
            changed.append((path, ""))
        if write:
            path.write_text(result.formatted, encoding="utf-8")

    for _, diff in changed:
        if diff:
            sys.stdout.write(diff)

    if args.check and changed:
        for path, _ in changed:
            print(f"would reformat {path}")
        print(f"apseudo-format: {len(changed)} file(s) would be reformatted.")
        return 1

    if not args.quiet:
        if write and changed:
            print(f"apseudo-format: reformatted {len(changed)} file(s).")
        elif args.diff and changed:
            print(f"apseudo-format: {len(changed)} file(s) differ.")
        else:
            print(f"apseudo-format: checked {len(paths)} file(s); no changes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
