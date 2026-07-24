"""Expose the local production package before its stage-oriented CLI is introduced."""

from __future__ import annotations

import argparse


def main(argv: list[str] | None = None) -> int:
    """Print the local production-pipeline help and return a process status."""
    parser = argparse.ArgumentParser(description="Repository explainer video pipeline")
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
