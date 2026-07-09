"""CLI for rendering Agent Pseudocode as Mermaid."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .mermaid import render_path, render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apseudo-mermaid",
        description="Render Pythonic Agent Pseudocode as a Mermaid flowchart view.",
    )
    parser.add_argument("path", nargs="?", type=Path, help="File to render. Reads stdin when omitted.")
    parser.add_argument("--config", type=Path, default=None, help="Explicit linter config file.")
    parser.add_argument("--no-fence", action="store_true", help="Emit raw Mermaid without Markdown code fences.")
    parser.add_argument("--version", action="version", version=f"apseudo-mermaid {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.path is None:
        result = render_text(sys.stdin.read(), name="stdin")
    else:
        config = load_config(start=args.path, explicit=args.config)
        result = render_path(args.path, config=config)
    if args.no_fence:
        print(result.source, end="")
    else:
        print("```mermaid")
        print(result.source, end="")
        print("```")
    if result.warning:
        print(f"apseudo-mermaid: {result.warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
