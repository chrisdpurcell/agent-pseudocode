"""CLI for generating Agent Pseudocode templates."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from . import __version__
from .templates import get_template, list_templates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apseudo-template",
        description="List or emit Pythonic Agent Pseudocode templates.",
    )
    parser.add_argument("template", nargs="?", help="Template name to emit.")
    parser.add_argument("--list", action="store_true", help="List available templates.")
    parser.add_argument("--json", action="store_true", help="Emit JSON metadata.")
    parser.add_argument("--version", action="version", version=f"apseudo-template {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list or args.template is None:
        templates = list_templates()
        if args.json:
            # asdict(), not __dict__: Template is a slots dataclass with no instance dict.
            print(
                json.dumps([asdict(template) for template in templates], indent=2, sort_keys=True)
            )
        else:
            for template in templates:
                print(f"{template.name}\t{template.title}\t{template.description}")
        return 0

    template = get_template(args.template)
    if template is None:
        print(f"apseudo-template: unknown template {args.template!r}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(asdict(template), indent=2, sort_keys=True))
    else:
        print(template.body, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
