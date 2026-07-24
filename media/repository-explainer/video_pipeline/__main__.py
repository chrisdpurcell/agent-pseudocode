"""Run the repository-local entry point for the explainer video production pipeline.

This module intentionally remains outside the installed toolkit. Its help surface is stable
while production stages are added, so automation can discover the local pipeline without
mistaking it for a public ``apseudo_lint`` command.
"""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    """Print the local production-pipeline help and return a process status."""
    parser = argparse.ArgumentParser(description="Repository explainer video pipeline")
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
