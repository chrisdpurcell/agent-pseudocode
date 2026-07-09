"""CLI for explaining Pythonic Agent Pseudocode rules."""

from __future__ import annotations

import argparse
import json
import sys

from . import __version__
from .rules import get_rule, list_rules


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apseudo-explain",
        description="Explain APSEUDO-* linter rules and approved convention guidance.",
    )
    parser.add_argument("codes", nargs="*", help="Rule codes to explain. Omit to list all rules.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown/text.")
    parser.add_argument("--version", action="version", version=f"apseudo-explain {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rules = list_rules() if not args.codes else []
    missing: list[str] = []
    for raw_code in args.codes:
        code = raw_code.upper()
        rule = get_rule(code)
        if rule is None:
            missing.append(code)
            continue
        rules.append(rule)

    if missing:
        print(f"apseudo-explain: unknown rule code(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([rule.__dict__ for rule in rules], indent=2, sort_keys=True))
        return 0

    if args.codes:
        print("\n\n".join(rule.as_markdown() for rule in rules))
        return 0

    for rule in rules:
        print(f"{rule.code}\t{rule.severity}\t{rule.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
