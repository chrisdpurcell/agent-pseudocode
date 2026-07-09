"""CLI for project-level Agent Pseudocode review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .review import review_project


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""

    parser = argparse.ArgumentParser(
        prog="apseudo-review",
        description="Review a repository for Agent Pseudocode convention/tooling completeness.",
    )
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd(), help="Repository root to review.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown.")
    parser.add_argument("--version", action="version", version=f"apseudo-review {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""

    args = build_parser().parse_args(argv)
    review = review_project(args.root)
    if args.json:
        print(json.dumps(review.as_dict(), indent=2, sort_keys=True))
    else:
        print(review.as_markdown(), end="")
    return 1 if review.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
